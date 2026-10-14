"""Hybrid search over `chunks`: keyword (tsquery) and vector (cosine), fused with RRF."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import LiteralString

from pgvector import Vector

from app.store_pg import PgConn

# Two CTEs, 40 candidates each; reciprocal rank fusion with k = 60; ties broken by chunk_key.
SEARCH: LiteralString = """
WITH semantic AS (
    SELECT chunk_key, row_number() OVER (ORDER BY dist, chunk_key) AS rnk
    FROM (
        SELECT chunk_key, embedding <=> %(emb)s AS dist
        FROM chunks
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %(emb)s
        LIMIT 40
    ) AS nearest
), keyword AS (
    SELECT chunk_key, row_number() OVER (ORDER BY kw DESC, chunk_key) AS rnk
    FROM (
        SELECT chunk_key, ts_rank_cd(tsv, websearch_to_tsquery('english', %(q)s)) AS kw
        FROM chunks
        WHERE tsv @@ websearch_to_tsquery('english', %(q)s)
        ORDER BY kw DESC, chunk_key
        LIMIT 40
    ) AS matches
), fused AS (
    SELECT chunk_key,
           coalesce(1.0 / (60 + semantic.rnk), 0) + coalesce(1.0 / (60 + keyword.rnk), 0) AS score
    FROM semantic FULL OUTER JOIN keyword USING (chunk_key)
)
SELECT p.url, c.anchor, c.heading_path, c.text, fused.score::float8 AS score
FROM fused
JOIN chunks c ON c.chunk_key = fused.chunk_key
JOIN pages p ON p.id = c.page_id
ORDER BY fused.score DESC, fused.chunk_key
LIMIT %(k)s
"""


@dataclass(frozen=True)
class Hit:
    url: str
    anchor: str
    heading_path: list[str]
    text: str
    score: float

    @property
    def citation(self) -> str:
        """The page URL plus the heading anchor: what the tutor cites."""
        return f"{self.url}#{self.anchor}" if self.anchor else self.url


def hybrid_search(
    conn: PgConn, query_embedding: Sequence[float], query_text: str, k: int = 8
) -> list[Hit]:
    rows = conn.execute(
        SEARCH, {"emb": Vector(list(query_embedding)), "q": query_text, "k": k}
    ).fetchall()
    conn.commit()
    return [Hit(r["url"], r["anchor"], r["heading_path"], r["text"], r["score"]) for r in rows]
