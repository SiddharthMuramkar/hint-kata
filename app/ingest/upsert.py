"""Write one page's chunks to Postgres: skip unchanged, upsert changed, delete vanished.

The tables are in app/pg_schema.sql (`pages`, `chunks`). Here `pages.source` is the track and
`pages.path` the manifest id. A chunk is unchanged when its content_sha256 (embed_text + model name)
matches the row with the same chunk_key, so a new model or an edited section re-embeds by itself.
"""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import LiteralString

from pgvector import Vector

from app.ingest.chunk import Chunk
from app.ingest.pipeline import Page
from app.store_pg import PgConn

HASHES: LiteralString = """
SELECT c.chunk_key, c.content_sha256
FROM chunks c JOIN pages p ON p.id = c.page_id
WHERE p.source = %s AND p.path = %s
"""

UPSERT_PAGE: LiteralString = """
INSERT INTO pages (source, path, url, title, version_ref, content_sha256)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (source, path) DO UPDATE SET
    url = EXCLUDED.url, title = EXCLUDED.title, version_ref = EXCLUDED.version_ref,
    content_sha256 = EXCLUDED.content_sha256
RETURNING id
"""

UPSERT_CHUNK: LiteralString = """
INSERT INTO chunks (chunk_key, page_id, anchor, heading_path, ordinal, text, embed_text,
                    content_sha256, embedding_model, embedding)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (chunk_key) DO UPDATE SET
    page_id = EXCLUDED.page_id, anchor = EXCLUDED.anchor, heading_path = EXCLUDED.heading_path,
    ordinal = EXCLUDED.ordinal, text = EXCLUDED.text, embed_text = EXCLUDED.embed_text,
    content_sha256 = EXCLUDED.content_sha256, embedding_model = EXCLUDED.embedding_model,
    embedding = EXCLUDED.embedding
"""

DIMS: LiteralString = """
SELECT atttypmod AS dims FROM pg_attribute
WHERE attrelid = 'chunks'::regclass AND attname = 'embedding'
"""

Embed = Callable[[list[str]], list[list[float]]]


@dataclass(frozen=True)
class Plan:
    """What a sync of one page will do."""

    to_embed: list[Chunk]  # new or changed
    unchanged: int
    vanished: list[str]  # chunk_keys in the database that the page no longer has


def check_dims(conn: PgConn, expected: int) -> None:
    """EMBED_DIMS must equal the size of the chunks.embedding column."""
    row = conn.execute(DIMS).fetchone()
    conn.commit()
    if row is None or row["dims"] != expected:
        have = row["dims"] if row else "no such column"
        raise ValueError(f"EMBED_DIMS is {expected} but chunks.embedding is vector({have})")


def plan_page(conn: PgConn, page: Page) -> Plan:
    rows = conn.execute(HASHES, (page.source, page.path)).fetchall()
    conn.commit()  # a read: do not sit idle in a transaction while we embed
    have = {r["chunk_key"]: r["content_sha256"] for r in rows}
    to_embed = [c for c in page.chunks if have.get(c.chunk_key) != c.content_sha256]
    keys = {c.chunk_key for c in page.chunks}
    return Plan(to_embed, len(page.chunks) - len(to_embed), sorted(set(have) - keys))


def apply_plan(conn: PgConn, page: Page, plan: Plan, vectors: Sequence[Sequence[float]]) -> None:
    """Upsert the page row and the changed chunks, delete the vanished ones: one transaction."""
    try:
        row = conn.execute(
            UPSERT_PAGE,
            (page.source, page.path, page.url, page.title, page.version_ref, page.content_sha256),
        ).fetchone()
        assert row is not None
        for c, vec in zip(plan.to_embed, vectors, strict=True):
            conn.execute(
                UPSERT_CHUNK,
                (
                    c.chunk_key,
                    row["id"],
                    c.anchor,
                    list(c.heading_path),
                    c.ordinal,
                    c.text,
                    c.embed_text,
                    c.content_sha256,
                    c.model,
                    Vector(list(vec)),
                ),
            )
        if plan.vanished:
            conn.execute("DELETE FROM chunks WHERE chunk_key = ANY(%s)", (plan.vanished,))
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def sync_page(conn: PgConn, page: Page, embed: Embed) -> Plan:
    """Embed only what changed, then write it. Returns what was done."""
    plan = plan_page(conn, page)
    vectors = embed([c.embed_text for c in plan.to_embed]) if plan.to_embed else []
    apply_plan(conn, page, plan, vectors)
    return plan
