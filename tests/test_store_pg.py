"""Run the SqliteStore behavioural tests against PostgresStore.

Needs a Postgres with pgvector: set TEST_DATABASE_URL (CI does; locally these tests skip).
The tests are imported from test_store.py, so pytest runs them again here with the Postgres
`store` fixture below.
"""

import os
from collections.abc import Iterator

import pytest
from psycopg.errors import ForeignKeyViolation

from app.store import Store
from app.store_pg import PostgresStore, apply_schema, open_pg_store
from tests.test_store import (  # noqa: F401  (imported so pytest collects them here)
    test_attempts,
    test_card_by_id,
    test_cards_upsert_get_review_log,
    test_chats,
    test_checks,
    test_due_cards_only_due_and_ordered,
    test_ensure_user_idempotent,
    test_events,
    test_grades,
    test_mastery,
    test_usable_from_another_thread,
)

URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set (needs Postgres)")


@pytest.fixture
def store() -> Iterator[PostgresStore]:
    assert URL
    apply_schema(URL)
    s = open_pg_store(URL)
    s.conn.execute(
        "TRUNCATE users, attempts, grades, cards, review_logs, chats, checks, mastery, events,"
        " pages, chunks RESTART IDENTITY CASCADE"
    )
    s.conn.commit()
    yield s
    s.close()


@pytest.fixture
def uid(store: PostgresStore) -> int:
    return store.ensure_user("ada")


def test_schema_version_and_idempotent() -> None:
    assert URL
    assert apply_schema(URL) == apply_schema(URL) == 1


def test_rag_tables_generate_tsv(store: PostgresStore) -> None:
    store.conn.execute("INSERT INTO pages (source, path) VALUES ('s', 'p')")
    store.conn.execute(
        "INSERT INTO chunks (chunk_key, page_id, heading_path, text)"
        " SELECT 'k', id, ARRAY['Install', 'Linux'], 'run the installer' FROM pages"
    )
    row = store.conn.execute(
        "SELECT count(*) AS n FROM chunks WHERE tsv @@ websearch_to_tsquery('english', 'installer')"
    ).fetchone()
    assert row is not None and row["n"] == 1


def test_foreign_keys_enforced(store: PostgresStore) -> None:
    with pytest.raises(ForeignKeyViolation):
        store.add_check(999, "l1", True, "out")


def test_postgres_store_is_a_store() -> None:
    assert URL
    s: Store = open_pg_store(URL)
    s.close()
