"""Unit tests for app/retrieval.py. The embedder is TestEmbeddingModel; the connection and the
search are fakes: no Postgres, no network. The track filter is tested in test_ingest_pg.py."""

import logging
import threading
from collections.abc import Callable, Iterator, Sequence
from types import TracebackType
from typing import Any

import psycopg
import pytest
from pydantic_ai import Embedder, models
from pydantic_ai.embeddings import EmbeddingResult, EmbeddingSettings, TestEmbeddingModel
from pydantic_ai.embeddings.result import EmbedInputType
from pydantic_ai.exceptions import UserError

from app import retrieval, store_pg
from app.config import Settings, settings
from app.ingest.search import Hit

DIMS = 1536


def hit(url: str = "https://docs.example/deps/", anchor: str = "a") -> Hit:
    return Hit(url, anchor, ["FastAPI", "Dependencies"], "text", 0.1)


class ThreadNoting(TestEmbeddingModel):
    """A test embedder that remembers which thread it was called on."""

    threads: list[int] = []

    async def embed(
        self,
        inputs: str | Sequence[str],
        *,
        input_type: EmbedInputType,
        settings: EmbeddingSettings | None = None,
    ) -> EmbeddingResult:
        self.threads.append(threading.get_ident())
        return await super().embed(inputs, input_type=input_type, settings=settings)


class FakeConn:
    """Stands in for a psycopg connection used as a context manager."""

    def __enter__(self) -> "FakeConn":
        return self

    def __exit__(
        self, kind: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        return None


class Calls:
    def __init__(self) -> None:
        self.search: list[dict[str, Any]] = []
        self.connects: list[dict[str, Any]] = []


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[Calls]:
    """A database URL is set, the embedder is a test one, and the search returns three hits."""
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    monkeypatch.setattr(settings, "database_url", "postgresql://example.invalid/db")
    monkeypatch.setattr(settings, "rag_enabled", True)
    retrieval._told.clear()
    ThreadNoting.threads = []
    c = Calls()

    def connect(url: str, *, connect_timeout: int | None = None) -> FakeConn:
        c.connects.append({"url": url, "connect_timeout": connect_timeout})
        return FakeConn()

    def search(
        conn: FakeConn,
        embedding: Sequence[float],
        text: str,
        k: int = 8,
        source: str | None = None,
    ) -> list[Hit]:
        c.search.append(
            {
                "dims": len(embedding),
                "text": text,
                "k": k,
                "source": source,
                "thread": threading.get_ident(),
            }
        )
        return [hit(), hit("javascript:alert(1)"), hit("https://docs.example/yield/", "b")]

    monkeypatch.setattr(retrieval, "make_embedder", lambda: Embedder(ThreadNoting(dimensions=DIMS)))
    monkeypatch.setattr(retrieval, "connect_pg", connect)
    monkeypatch.setattr(retrieval, "hybrid_search", search)
    yield c
    retrieval._told.clear()


def test_retrieve_embeds_the_question_and_searches_the_lesson_track(calls: Calls) -> None:
    hits = retrieval.retrieve("how do I use Depends?", track="fastapi", k=3)
    assert [h.url for h in hits] == ["https://docs.example/deps/", "https://docs.example/yield/"]
    assert [{k: v for k, v in s.items() if k != "thread"} for s in calls.search] == [
        {"dims": DIMS, "text": "how do I use Depends?", "k": 3, "source": "fastapi"}
    ]
    # the pooled DATABASE_URL, and a connect timeout so a hung connect cannot pile up threads
    assert calls.connects == [
        {"url": "postgresql://example.invalid/db", "connect_timeout": retrieval.CONNECT_TIMEOUT_S}
    ]
    assert retrieval.CONNECT_TIMEOUT_S == 5


def test_no_track_means_no_filter(calls: Calls) -> None:
    retrieval.retrieve("question", track="")
    assert calls.search[0]["source"] is None and calls.search[0]["k"] == 6


def test_a_blank_question_is_not_searched(calls: Calls) -> None:
    assert retrieval.retrieve("  \n", track="fastapi") == []
    assert calls.search == [] and calls.connects == []


def test_without_database_url_it_returns_nothing_and_says_so_once(
    calls: Calls, monkeypatch: pytest.MonkeyPatch, app_logs: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(settings, "database_url", "")
    assert retrieval.retrieve("one", track="fastapi") == []
    assert retrieval.retrieve("two", track="fastapi") == []
    told = [r for r in app_logs.records if r.name == "app.retrieval"]
    assert [r.levelno for r in told] == [logging.INFO, logging.DEBUG]  # said once, then quiet
    assert "DATABASE_URL is not set" in told[0].getMessage()
    assert calls.connects == [] and calls.search == []


def fail_with(error: Exception) -> Callable[..., Any]:
    def boom(*args: Any, **kwargs: Any) -> Any:
        raise error

    return boom


@pytest.mark.parametrize(
    "broken",
    [
        pytest.param(("make_embedder", UserError("Set OPENROUTER_API_KEY")), id="no-embedding-key"),
        pytest.param(("connect_pg", psycopg.OperationalError("connection refused")), id="no-db"),
        pytest.param(
            ("hybrid_search", psycopg.errors.UndefinedTable('relation "chunks" does not exist')),
            id="tables-missing",
        ),
    ],
)
def test_a_missing_key_database_or_table_means_no_hits_logged_once(
    calls: Calls,
    monkeypatch: pytest.MonkeyPatch,
    app_logs: pytest.LogCaptureFixture,
    broken: tuple[str, Exception],
) -> None:
    name, error = broken
    monkeypatch.setattr(retrieval, name, fail_with(error))
    assert retrieval.retrieve("question", track="fastapi") == []
    assert retrieval.retrieve("question", track="fastapi") == []
    assert [r.levelno for r in app_logs.records if r.name == "app.retrieval"] == [
        logging.INFO,
        logging.DEBUG,
    ]


def test_different_errors_of_the_same_kind_are_each_told_once(
    calls: Calls, monkeypatch: pytest.MonkeyPatch, app_logs: pytest.LogCaptureFixture
) -> None:
    for message in ("connection refused", "connection refused", "password authentication failed"):
        monkeypatch.setattr(retrieval, "connect_pg", fail_with(psycopg.OperationalError(message)))
        retrieval.retrieve("question", track="fastapi")
    told = [(r.levelno, r.getMessage()) for r in app_logs.records if r.name == "app.retrieval"]
    assert [level for level, _ in told] == [logging.INFO, logging.DEBUG, logging.INFO]
    assert "password authentication failed" in told[2][1]


def test_a_model_with_the_wrong_vector_size_means_no_hits(
    calls: Calls, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        retrieval, "make_embedder", lambda: Embedder(TestEmbeddingModel(dimensions=8))
    )
    assert retrieval.retrieve("question", track="fastapi") == []
    assert calls.search == []


@pytest.mark.anyio
async def test_retrieve_async_embeds_on_the_request_loop_and_searches_in_a_thread(
    calls: Calls,
) -> None:
    hits = await retrieval.retrieve_async("question", track="github", k=2)
    assert len(hits) == 2 and calls.search[0]["source"] == "github" and calls.search[0]["k"] == 2
    here = threading.get_ident()
    assert ThreadNoting.threads == [here]  # the HTTP client's loop, not a worker thread's own
    assert calls.search[0]["thread"] != here  # only the blocking psycopg call is threaded


@pytest.mark.anyio
async def test_retrieve_async_is_off_when_rag_is_disabled(
    calls: Calls, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "rag_enabled", False)
    assert await retrieval.retrieve_async("question", track="github") == []
    assert calls.connects == [] and ThreadNoting.threads == []


@pytest.mark.anyio
async def test_retrieve_async_does_not_embed_without_a_database(
    calls: Calls, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "database_url", "")
    assert await retrieval.retrieve_async("question", track="github") == []
    assert ThreadNoting.threads == []  # no paid embedding call for a search that cannot run


@pytest.mark.anyio
async def test_retrieve_async_turns_any_error_into_no_hits(
    calls: Calls, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(retrieval, "search", fail_with(RuntimeError("bug")))
    assert await retrieval.retrieve_async("question", track="github") == []


def test_connect_pg_passes_the_connect_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, Any] = {}

    class FakeConnection:
        @classmethod
        def connect(cls, url: str, **kwargs: Any) -> "FakeConnection":
            seen.update(kwargs)
            return cls()

        def commit(self) -> None:
            return None

    monkeypatch.setattr(store_pg, "PgConn", FakeConnection)
    monkeypatch.setattr(store_pg, "register_vector", lambda conn: None)
    store_pg.connect_pg("postgresql://example.invalid/db", connect_timeout=5)
    assert seen["connect_timeout"] == 5
    store_pg.connect_pg("postgresql://example.invalid/db")
    assert seen["connect_timeout"] is None  # psycopg drops None, so the default is unchanged


@pytest.mark.parametrize(("given", "kept"), [(-3, 1), (0, 1), (1, 1), (6, 6), (10, 10), (99, 10)])
def test_rag_k_is_clamped_to_1_to_10(given: int, kept: int) -> None:
    assert Settings(rag_k=given).rag_k == kept
