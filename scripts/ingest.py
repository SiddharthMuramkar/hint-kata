"""Ingest the cached docs (see scripts/fetch_docs.py) into Postgres: chunk, embed, upsert.

Usage: uv run python scripts/ingest.py [--only id[,id...]] [--dry-run | --check | --prune]
       [--manifest content/sources.yaml] [--cache .cache/docs]

  --dry-run  chunk the cached pages and print counts and sizes. No embedding, no database.
  --check    compare the chunks with the database and report what a real run would embed or delete,
             and which stored pages are no longer in the manifest. Exit code 1 if anything differs.
             Reads only; needs DATABASE_URL_UNPOOLED.
  --prune    delete the pages (and their chunks) that are in the database but no longer in the
             manifest, or are now `kind: link`. Add --dry-run to only list them. Looks at the whole
             manifest, so it cannot be combined with --only or --check. Needs DATABASE_URL_UNPOOLED.
  (none)     embed the new or changed chunks, upsert them, delete the vanished ones. Needs
             OPENROUTER_API_KEY and DATABASE_URL_UNPOOLED in the local env file, and
             `scripts/migrate.py` run once.

`kind: link` entries are never fetched, so they are skipped everywhere. Pages whose chunks are
unchanged cost nothing. Fetched docs are untrusted data: we only read them.
"""

import argparse
import sys
from pathlib import Path

import psycopg
from pydantic_ai import Embedder
from pydantic_ai.exceptions import ModelAPIError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports from scripts/

from app.config import settings  # noqa: E402
from app.ingest.chunk import tokens  # noqa: E402
from app.ingest.embed import embed_texts, make_embedder  # noqa: E402
from app.ingest.pipeline import (  # noqa: E402
    Entry,
    build_page,
    cache_file,
    is_link,
    load_entries,
    missing_pages,
)
from app.ingest.upsert import (  # noqa: E402
    check_dims,
    delete_pages,
    plan_page,
    stale_pages,
    sync_page,
)
from app.store_pg import PgConn, connect_pg  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FAILURES = (ValueError, ModelAPIError, psycopg.Error)


def wanted(manifest: Path) -> set[tuple[str, str]]:
    """The (track, id) of every page that should be in the database: all but link-only entries."""
    keep = {(e["track"], e["id"]) for e in load_entries(manifest) if not is_link(e)}
    if not keep:
        raise SystemExit("error: the manifest lists no ingestable sources; refusing to go on.")
    return keep


def select(manifest: Path, cache: Path, only: list[str]) -> list[Entry]:
    """The entries to ingest. Link-only ones are skipped (no cache file is expected for them)."""
    ids = [i for part in only for i in part.split(",") if i]
    try:
        entries = load_entries(manifest, ids or None)
    except ValueError as e:
        raise SystemExit(f"error: {e}") from None
    if links := [e for e in entries if is_link(e)]:
        print(f"skipped {len(links)} link-only source(s): never fetched, never ingested")
    entries = [e for e in entries if not is_link(e)]
    if missing := missing_pages(entries, cache):
        lines = "\n".join(f"  {e['id']}  (expected {cache_file(cache, e)})" for e in missing)
        raise SystemExit(
            f"error: {len(missing)} cached page(s) missing:\n{lines}\n"
            "Fetch them first: uv run python scripts/fetch_docs.py [--only <id>]"
        )
    return entries


def database_url() -> str:
    if not settings.database_url_unpooled:
        raise SystemExit("error: set DATABASE_URL_UNPOOLED in the local env file first.")
    return settings.database_url_unpooled


def dry_run(entries: list[Entry], cache: Path) -> int:
    total = 0
    for e in entries:
        page = build_page(e, cache, settings.embed_model)
        sizes = [tokens(c.embed_text) for c in page.chunks] or [0]
        print(
            f"{e['id']:<58}{len(page.chunks):>4} chunks  "
            f"tokens min {min(sizes)} / avg {sum(sizes) // len(sizes)} / max {max(sizes)}"
        )
        total += len(page.chunks)
    print(f"dry-run: {len(entries)} pages, {total} chunks (nothing embedded, no database used)")
    return 0


def report_stale(conn: PgConn, keep: set[tuple[str, str]], delete: bool) -> int:
    """Print the stored pages that are not in `keep`; delete them if `delete`. Returns how many."""
    stale = stale_pages(conn, keep)
    verb = "deleted" if delete else "would delete"
    for s in stale:
        print(f"{verb:<13}{s.source}/{s.path}  ({s.chunks} chunks)")
    if stale and delete:
        delete_pages(conn, stale)
    return len(stale)


def prune(manifest: Path, dry: bool) -> int:
    keep = wanted(manifest)
    n = report_stale(connect_pg(database_url()), keep, delete=not dry)
    print(f"prune: {n} page(s) {'would be ' if dry else ''}removed from the database")
    return 0


def check(entries: list[Entry], cache: Path, keep: set[tuple[str, str]] | None) -> int:
    conn = connect_pg(database_url())
    differs = 0
    for e in entries:
        plan = plan_page(conn, build_page(e, cache, settings.embed_model))
        differs += bool(plan.to_embed or plan.vanished)
        status = "CHANGED" if plan.to_embed or plan.vanished else "ok"
        print(
            f"{status:<9}{e['id']:<58}to embed {len(plan.to_embed)}, "
            f"unchanged {plan.unchanged}, to delete {len(plan.vanished)}"
        )
    stale = report_stale(conn, keep, delete=False) if keep else 0
    if stale:
        print("(those pages are no longer in the manifest: remove them with --prune)")
    print(f"check: {differs} of {len(entries)} pages differ from the database, {stale} stale")
    return 1 if differs or stale else 0


def ingest(entries: list[Entry], cache: Path, embedder: Embedder) -> int:
    conn = connect_pg(database_url())
    check_dims(conn, settings.embed_dims)
    done = embedded = deleted = 0
    for e in entries:
        try:
            page = build_page(e, cache, settings.embed_model)
            plan = sync_page(conn, page, lambda texts: embed_texts(embedder, texts))
        except FAILURES as err:
            kept = (
                f"\n{done} page(s) written so far are kept; run again to continue." if done else ""
            )
            raise SystemExit(f"error: {e['id']}: {err}{kept}") from None
        done += 1
        embedded += len(plan.to_embed)
        deleted += len(plan.vanished)
        print(
            f"ok       {e['id']:<58}{len(page.chunks):>4} chunks: embedded {len(plan.to_embed)}, "
            f"unchanged {plan.unchanged}, deleted {len(plan.vanished)}"
        )
    print(f"ingest: {done} pages, {embedded} chunks embedded, {deleted} deleted")
    return 0


def main(argv: list[str] | None = None, *, embedder: Embedder | None = None) -> int:
    ap = argparse.ArgumentParser(description="Chunk, embed and upsert the cached docs.")
    ap.add_argument("--manifest", type=Path, default=ROOT / "content" / "sources.yaml")
    ap.add_argument("--cache", type=Path, default=ROOT / ".cache" / "docs")
    ap.add_argument("--only", action="append", default=[], help="source id(s), comma separated")
    ap.add_argument("--dry-run", action="store_true", help="no embedding; with --prune, no delete")
    ap.add_argument("--check", action="store_true", help="compare with the database, read-only")
    ap.add_argument("--prune", action="store_true", help="delete pages no longer in the manifest")
    args = ap.parse_args(argv)
    if args.dry_run and args.check:
        ap.error("--dry-run and --check cannot be combined")
    if args.prune and (args.check or args.only):
        ap.error("--prune looks at the whole manifest: do not combine it with --check or --only")

    try:
        if args.prune:
            return prune(args.manifest, args.dry_run)
        entries = select(args.manifest, args.cache, args.only)
        if args.dry_run:
            return dry_run(entries, args.cache)
        if args.check:
            return check(entries, args.cache, None if args.only else wanted(args.manifest))
        if not entries:
            print("nothing to ingest")
            return 0
        if embedder is None:
            if settings.embed_model.startswith("openrouter:") and not settings.openrouter_api_key:
                raise SystemExit("error: set OPENROUTER_API_KEY in the local env file first.")
            embedder = make_embedder()
        return ingest(entries, args.cache, embedder)
    except psycopg.errors.UndefinedTable:
        raise SystemExit(
            "error: the tables are missing. Run: uv run python scripts/migrate.py"
        ) from None
    except FAILURES as e:
        raise SystemExit(f"error: {e}") from None


if __name__ == "__main__":
    sys.exit(main())
