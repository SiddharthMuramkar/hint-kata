"""Ingest the cached docs (see scripts/fetch_docs.py) into Postgres: chunk, embed, upsert.

Usage: uv run python scripts/ingest.py [--only id[,id...]] [--dry-run | --check]
       [--manifest content/sources.yaml] [--cache .cache/docs]

  --dry-run  chunk the cached pages and print counts and sizes. No embedding, no database.
  --check    compare the chunks with the database and report what a real run would embed or delete.
             Exit code 1 if anything differs. Reads only; needs DATABASE_URL_UNPOOLED.
  (neither)  embed the new or changed chunks, upsert them, delete the vanished ones. Needs
             OPENROUTER_API_KEY and DATABASE_URL_UNPOOLED in the local env file, and
             `scripts/migrate.py` run once.

Pages whose chunks are unchanged cost nothing. Fetched docs are untrusted data: we only read them.
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
    load_entries,
    missing_pages,
)
from app.ingest.upsert import check_dims, plan_page, sync_page  # noqa: E402
from app.store_pg import connect_pg  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def select(manifest: Path, cache: Path, only: list[str]) -> list[Entry]:
    ids = [i for part in only for i in part.split(",") if i]
    try:
        entries = load_entries(manifest, ids or None)
    except ValueError as e:
        raise SystemExit(f"error: {e}") from None
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


def check(entries: list[Entry], cache: Path) -> int:
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
    print(f"check: {differs} of {len(entries)} pages differ from the database")
    return 1 if differs else 0


def ingest(entries: list[Entry], cache: Path, embedder: Embedder) -> int:
    conn = connect_pg(database_url())
    check_dims(conn, settings.embed_dims)
    done = embedded = deleted = 0
    for e in entries:
        page = build_page(e, cache, settings.embed_model)
        plan = sync_page(conn, page, lambda texts: embed_texts(embedder, texts))
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
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true", help="chunk only: no embedding, no database"
    )
    mode.add_argument("--check", action="store_true", help="compare with the database, read-only")
    args = ap.parse_args(argv)

    entries = select(args.manifest, args.cache, args.only)
    if args.dry_run:
        return dry_run(entries, args.cache)
    try:
        if args.check:
            return check(entries, args.cache)
        if embedder is None:
            if settings.embed_model.startswith("openrouter:") and not settings.openrouter_api_key:
                raise SystemExit("error: set OPENROUTER_API_KEY in the local env file first.")
            embedder = make_embedder()
        return ingest(entries, args.cache, embedder)
    except psycopg.errors.UndefinedTable:
        raise SystemExit(
            "error: the tables are missing. Run: uv run python scripts/migrate.py"
        ) from None
    except (ValueError, ModelAPIError, psycopg.Error) as e:
        raise SystemExit(
            f"error: {e}\nPages already written are kept; run again to continue."
        ) from None


if __name__ == "__main__":
    sys.exit(main())
