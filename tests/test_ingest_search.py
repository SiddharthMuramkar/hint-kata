"""hybrid_search without a database: which SET LOCAL statements it sends. The SQL itself runs in
test_ingest_pg.py."""

from typing import Any, cast

import pytest

from app.ingest import search
from app.store_pg import PgConn


@pytest.mark.parametrize(
    ("extversion", "expected"),
    [
        ("0.7.4", False),
        ("0.8.0", True),
        ("0.8.1", True),
        ("0.10.0", True),
        ("1.0.0", True),
        ("0.8", True),
        (None, False),  # the extension is not installed
        ("", False),
        ("dev", False),
    ],
)
def test_supports_iterative_scan_from_the_extension_version(
    extversion: str | None, expected: bool
) -> None:
    assert search.supports_iterative_scan(extversion) is expected


class FakeConn:
    """Records the SQL; answers the pgvector version probe and returns no rows."""

    def __init__(self, extversion: str | None) -> None:
        self.extversion = extversion
        self.statements: list[str] = []

    def execute(self, sql: str, params: Any = None) -> "FakeConn":
        self.statements.append(sql.strip().split("\n")[0][:60])
        return self

    def fetchone(self) -> dict[str, str] | None:
        return {"extversion": self.extversion} if self.extversion else None

    def fetchall(self) -> list[dict[str, Any]]:
        return []

    def commit(self) -> None:
        return None


@pytest.fixture(autouse=True)
def _probe_afresh(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(search, "_iterative_scan", None)


def run(extversion: str | None, source: str | None) -> list[str]:
    conn = FakeConn(extversion)
    search.hybrid_search(cast(PgConn, conn), [0.0] * 4, "q", source=source)
    return conn.statements


def test_a_filtered_search_turns_on_iterative_scan_when_pgvector_is_new_enough() -> None:
    statements = run("0.8.0", "fastapi")
    assert "SET LOCAL hnsw.ef_search = 100" in statements
    assert "SET LOCAL hnsw.iterative_scan = relaxed_order" in statements


def test_an_old_pgvector_never_gets_the_setting_that_would_abort_the_transaction() -> None:
    statements = run("0.7.4", "fastapi")
    assert "SET LOCAL hnsw.ef_search = 100" in statements
    assert "SET LOCAL hnsw.iterative_scan = relaxed_order" not in statements


def test_an_unfiltered_search_does_not_even_ask_the_version() -> None:
    statements = run("0.8.0", None)
    assert not any("pg_extension" in s for s in statements)
    assert "SET LOCAL hnsw.iterative_scan = relaxed_order" not in statements


def test_the_version_is_asked_once_per_process() -> None:
    first = run("0.8.0", "fastapi")
    second = run("0.8.0", "github")
    assert sum("pg_extension" in s for s in first) == 1
    assert not any("pg_extension" in s for s in second)
    assert "SET LOCAL hnsw.iterative_scan = relaxed_order" in second
