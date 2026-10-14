"""Ingestion against Postgres with pgvector: incremental upsert and hybrid search.

Needs a Postgres with pgvector: set TEST_DATABASE_URL (CI does; locally these tests skip).
Embeddings come from TestEmbeddingModel or are written by hand: nothing calls the network.
"""

import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import LiteralString

import psycopg
import pytest
from pydantic_ai import Embedder
from pydantic_ai.embeddings import TestEmbeddingModel

from app.config import settings
from app.ingest.chunk import chunk_page, sha256
from app.ingest.embed import embed_texts
from app.ingest.pipeline import Page, build_page, load_entries
from app.ingest.search import hybrid_search
from app.ingest.upsert import Plan, apply_plan, check_dims, plan_page, sync_page
from app.store_pg import PgConn, apply_schema, connect_pg
from tests.test_ingest_chunk import doc, words
from tests.test_ingest_cli import ing, make_site

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set (needs Postgres)")
DIMS = 1536


@pytest.fixture
def conn() -> Iterator[PgConn]:
    assert URL
    apply_schema(URL)
    c = connect_pg(URL)
    c.execute("TRUNCATE pages, chunks RESTART IDENTITY CASCADE")
    c.commit()
    yield c
    c.close()


class Embeds:
    """An embed callback that remembers every text it was asked for."""

    def __init__(self) -> None:
        self.texts: list[str] = []
        self.embedder = Embedder(TestEmbeddingModel(dimensions=DIMS))

    def __call__(self, texts: list[str]) -> list[list[float]]:
        self.texts += texts
        return embed_texts(self.embedder, texts)


def sections(a: str = "alpha", b: str = "beta", c: str | None = "gamma") -> str:
    parts = [f"## A\n\n{words(150, a)}", f"## B\n\n{words(150, b)}"]
    return doc(*parts, *([f"## C\n\n{words(150, c)}"] if c else []))


def page_of(markdown: str, path: str = "p1", model: str = "m1") -> Page:
    return Page(
        "fastapi",
        path,
        f"https://docs.example/{path}/",
        "Page title",
        "1.0",
        sha256(markdown),
        chunk_page(path, "fastapi", "Page title", markdown, model),
    )


def one_hot(i: int, weight: float = 1.0) -> list[float]:
    return [weight if j == i else 0.0 for j in range(DIMS)]


CHUNKS: LiteralString = "SELECT count(*) AS n FROM chunks"
PAGES: LiteralString = "SELECT count(*) AS n FROM pages"


def count(conn: PgConn, sql: LiteralString) -> int:
    row = conn.execute(sql).fetchone()
    conn.commit()
    assert row is not None
    return row["n"]


def test_embed_dims_must_match_the_column(conn: PgConn) -> None:
    check_dims(conn, DIMS)
    with pytest.raises(ValueError, match=r"EMBED_DIMS is 8 but chunks.embedding is vector\(1536\)"):
        check_dims(conn, 8)
    assert settings.embed_dims == DIMS


def test_first_sync_writes_the_page_and_every_chunk(conn: PgConn) -> None:
    page = page_of(sections())
    embeds = Embeds()
    plan = sync_page(conn, page, embeds)
    assert [c.anchor for c in plan.to_embed] == ["a", "b", "c"]
    assert plan.unchanged == 0 and plan.vanished == []
    rows = conn.execute(
        "SELECT chunk_key, anchor, heading_path, embedding_model, content_sha256,"
        " vector_dims(embedding) AS dims FROM chunks ORDER BY anchor"
    ).fetchall()
    assert [r["anchor"] for r in rows] == ["a", "b", "c"]
    assert rows[0]["heading_path"] == ["FastAPI", "Page title", "A"]
    assert {r["embedding_model"] for r in rows} == {"m1"} and {r["dims"] for r in rows} == {DIMS}
    assert [r["content_sha256"] for r in rows] == [c.content_sha256 for c in page.chunks]
    pg = conn.execute("SELECT * FROM pages").fetchone()
    assert pg is not None
    assert (pg["source"], pg["path"], pg["url"], pg["title"], pg["version_ref"]) == (
        "fastapi",
        "p1",
        "https://docs.example/p1/",
        "Page title",
        "1.0",
    )
    assert pg["content_sha256"] == page.content_sha256


def test_a_second_run_embeds_nothing(conn: PgConn) -> None:
    embeds = Embeds()
    sync_page(conn, page_of(sections()), embeds)
    seen = len(embeds.texts)
    plan = sync_page(conn, page_of(sections()), embeds)
    assert plan.to_embed == [] and plan.unchanged == 3 and plan.vanished == []
    assert len(embeds.texts) == seen  # no request at all
    assert count(conn, CHUNKS) == 3 and count(conn, PAGES) == 1


def test_an_edit_embeds_only_the_changed_chunk(conn: PgConn) -> None:
    embeds = Embeds()
    sync_page(conn, page_of(sections()), embeds)
    before = len(embeds.texts)
    plan = sync_page(conn, page_of(sections(b="delta")), embeds)
    assert [c.anchor for c in plan.to_embed] == ["b"] and plan.unchanged == 2
    assert len(embeds.texts) == before + 1
    row = conn.execute("SELECT text FROM chunks WHERE anchor = 'b'").fetchone()
    assert row is not None and "delta" in row["text"]
    assert count(conn, CHUNKS) == 3


def test_vanished_chunks_are_deleted_and_other_pages_are_left_alone(conn: PgConn) -> None:
    embeds = Embeds()
    sync_page(conn, page_of(sections(), "p1"), embeds)
    sync_page(conn, page_of(sections(), "p2"), embeds)
    plan = sync_page(conn, page_of(sections(c=None), "p1"), embeds)
    assert len(plan.vanished) == 1 and plan.to_embed == []
    assert count(conn, "SELECT count(*) AS n FROM chunks WHERE anchor = 'c'") == 1  # only p2's
    per_page: LiteralString = (
        "SELECT count(*) AS n FROM chunks c JOIN pages p ON p.id = c.page_id WHERE p.path = "
    )
    assert count(conn, per_page + "'p1'") == 2
    assert count(conn, per_page + "'p2'") == 3


def test_a_new_model_embeds_everything_again(conn: PgConn) -> None:
    embeds = Embeds()
    sync_page(conn, page_of(sections(), model="m1"), embeds)
    plan = sync_page(conn, page_of(sections(), model="m2"), embeds)
    assert len(plan.to_embed) == 3 and plan.unchanged == 0
    assert count(conn, CHUNKS) == 3
    assert count(conn, "SELECT count(*) AS n FROM chunks WHERE embedding_model = 'm2'") == 3


def test_a_failed_write_changes_nothing(conn: PgConn) -> None:
    page = page_of(sections())
    plan = plan_page(conn, page)
    vectors = [one_hot(0), [1.0] * 8, one_hot(2)]  # the second has the wrong size
    with pytest.raises(psycopg.Error):
        apply_plan(conn, page, plan, vectors)
    assert count(conn, CHUNKS) == 0 and count(conn, PAGES) == 0


def _search_page(conn: PgConn) -> None:
    page = page_of(
        doc(
            f"## A\n\n{words(150, 'pooler')}",
            f"## B\n\n{words(150, 'filler')}",
            f"## C\n\n{words(150, 'pooler')}",
        )
    )
    apply_plan(conn, page, plan_page(conn, page), [one_hot(0), one_hot(1), one_hot(2)])


def test_hybrid_search_fuses_vector_and_keyword_ranks(conn: PgConn) -> None:
    _search_page(conn)
    query = [a + b for a, b in zip(one_hot(0), one_hot(1, 0.5), strict=True)]  # near A, then B
    hits = hybrid_search(conn, query, "pooler", k=8)
    # A is first in the vector list and has the keyword; C has the keyword; B has neither.
    assert [h.anchor for h in hits] == ["a", "c", "b"]
    assert hits[0].citation == "https://docs.example/p1/#a"
    assert hits[0].heading_path == ["FastAPI", "Page title", "A"]
    assert "pooler" in hits[0].text and hits[0].score > hits[1].score > hits[2].score
    assert [h.anchor for h in hybrid_search(conn, query, "pooler", k=2)] == ["a", "c"]


def test_hybrid_search_understands_web_search_syntax_and_empty_text(conn: PgConn) -> None:
    _search_page(conn)
    query = one_hot(0)
    # "filler -pooler" matches only B, so B beats A even though A is nearer in vector space.
    assert hybrid_search(conn, query, "filler -pooler", k=3)[0].anchor == "b"
    assert [h.anchor for h in hybrid_search(conn, query, "", k=3)][0] == "a"  # vector only
    assert len(hybrid_search(conn, query, "nomatchatall", k=3)) == 3


def test_the_script_ingests_checks_and_resyncs(
    conn: PgConn,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(settings, "database_url_unpooled", URL)
    manifest, cache = make_site(tmp_path)
    args = ["--manifest", str(manifest), "--cache", str(cache)]
    embedder = Embedder(TestEmbeddingModel(dimensions=DIMS))
    total = sum(
        len(build_page(e, cache, settings.embed_model).chunks) for e in load_entries(manifest)
    )

    assert ing.main(args, embedder=embedder) == 0
    assert f"ingest: 3 pages, {total} chunks embedded, 0 deleted" in capsys.readouterr().out
    assert count(conn, CHUNKS) == total

    assert ing.main([*args, "--check"]) == 0
    assert "0 of 3 pages differ" in capsys.readouterr().out
    assert ing.main(args, embedder=embedder) == 0
    assert "0 chunks embedded" in capsys.readouterr().out

    page = cache / "github" / "github-protected-branches.md"
    page.write_text(page.read_text(encoding="utf-8") + f"\n## New part\n\n{words(150)}\n")
    assert ing.main([*args, "--check"]) == 1
    assert "CHANGED  github-protected-branches" in capsys.readouterr().out
    assert ing.main(args, embedder=embedder) == 0
    out = capsys.readouterr().out
    embedded = re.search(r"(\d+) chunks embedded", out)
    assert embedded is not None and int(embedded[1]) >= 1
    for other in ("fastapi-dependencies", "pydantic-ai-install"):
        assert re.search(rf"{other}\s+\d+ chunks: embedded 0,", out)  # untouched pages cost nothing
    assert ing.main([*args, "--check"]) == 0


def test_plan_page_is_read_only(conn: PgConn) -> None:
    plan: Plan = plan_page(conn, page_of(sections()))
    assert len(plan.to_embed) == 3
    assert count(conn, PAGES) == 0 and count(conn, CHUNKS) == 0
