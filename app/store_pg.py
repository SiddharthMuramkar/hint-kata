"""Postgres (Neon) persistence. Same Store Protocol as SqliteStore; all SQL lives here."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, LiteralString, cast

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

PgConn = psycopg.Connection[dict[str, Any]]
SCHEMA = Path(__file__).with_name("pg_schema.sql")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def apply_schema(url_unpooled: str) -> int:
    """Create the tables (idempotent) and return the schema version. Use the direct
    (unpooled) Neon URL: DDL through PgBouncer can fail."""
    with PgConn.connect(url_unpooled, row_factory=dict_row) as conn:
        conn.execute(cast(LiteralString, SCHEMA.read_text()))
        row = conn.execute("SELECT max(version) AS v FROM schema_version").fetchone()
    assert row is not None
    return row["v"]


def connect_pg(url: str) -> PgConn:
    """Open a connection (autocommit off). The schema must already be applied, because
    register_vector needs the vector extension. On a pooled Neon URL (PgBouncer, transaction
    mode) never use a session SET; use SET LOCAL inside a transaction."""
    conn = PgConn.connect(url, row_factory=dict_row)
    register_vector(conn)
    conn.commit()  # end the type-lookup transaction; do not sit idle in transaction
    return conn


class PostgresStore:
    def __init__(self, conn: PgConn) -> None:
        self.conn = conn

    def _all(self, sql: LiteralString, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        """Run one statement, commit, return its rows (if any)."""
        try:
            cur = self.conn.execute(sql, params)
            rows = cur.fetchall() if cur.description else []
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        return rows

    def _write(self, sql: LiteralString, params: tuple[Any, ...]) -> int:
        """Run one INSERT ... RETURNING id, commit, return the id."""
        return self._all(sql, params)[0]["id"]

    def _one(self, sql: LiteralString, params: tuple[Any, ...]) -> dict[str, Any] | None:
        rows = self._all(sql, params)
        return rows[0] if rows else None

    def ensure_user(self, name: str) -> int:
        self._all(
            "INSERT INTO users (name, created_at) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
            (name, _now()),
        )
        row = self._one("SELECT id FROM users WHERE name = %s", (name,))
        assert row is not None
        return row["id"]

    def add_attempt(
        self,
        user_id: int,
        lesson_id: str,
        item_id: str,
        kind: str,
        answer: str,
        correct: bool,
        confidence: str,
        try_no: int,
        elapsed_ms: int,
    ) -> int:
        return self._write(
            "INSERT INTO attempts (user_id, lesson_id, item_id, kind, answer, correct,"
            " confidence, try_no, elapsed_ms, created_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (
                user_id,
                lesson_id,
                item_id,
                kind,
                answer,
                correct,
                confidence,
                try_no,
                elapsed_ms,
                _now(),
            ),
        )

    def attempts_for(self, user_id: int, lesson_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM attempts WHERE user_id = %s AND lesson_id = %s ORDER BY id",
            (user_id, lesson_id),
        )

    def add_grade(
        self,
        user_id: int,
        lesson_id: str,
        question_id: str,
        attempt_no: int,
        answer: str,
        result_json: str,
        flagged: bool,
    ) -> int:
        return self._write(
            "INSERT INTO grades (user_id, lesson_id, question_id, attempt_no, answer,"
            " result_json, flagged, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            " RETURNING id",
            (user_id, lesson_id, question_id, attempt_no, answer, result_json, flagged, _now()),
        )

    def grades_for(self, user_id: int, lesson_id: str, question_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM grades WHERE user_id = %s AND lesson_id = %s AND question_id = %s"
            " ORDER BY id",
            (user_id, lesson_id, question_id),
        )

    def upsert_card(
        self,
        user_id: int,
        item_key: str,
        lesson_id: str,
        card_json: str,
        due: str,
        last_rating: int | None,
    ) -> int:
        return self._write(
            "INSERT INTO cards (user_id, item_key, lesson_id, card_json, due, last_rating,"
            " updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            " ON CONFLICT (user_id, item_key) DO UPDATE SET lesson_id = excluded.lesson_id,"
            " card_json = excluded.card_json, due = excluded.due,"
            " last_rating = excluded.last_rating, updated_at = excluded.updated_at"
            " RETURNING id",
            (user_id, item_key, lesson_id, card_json, due, last_rating, _now()),
        )

    def get_card(self, user_id: int, item_key: str) -> dict[str, Any] | None:
        return self._one(
            "SELECT * FROM cards WHERE user_id = %s AND item_key = %s", (user_id, item_key)
        )

    def card_by_id(self, user_id: int, card_id: int) -> dict[str, Any] | None:
        return self._one("SELECT * FROM cards WHERE user_id = %s AND id = %s", (user_id, card_id))

    def due_cards(self, user_id: int, now_iso: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM cards WHERE user_id = %s AND due <= %s ORDER BY due, id LIMIT %s",
            (user_id, now_iso, limit),
        )

    def add_review_log(self, card_id: int, log_json: str) -> int:
        return self._write(
            "INSERT INTO review_logs (card_id, log_json, created_at) VALUES (%s, %s, %s)"
            " RETURNING id",
            (card_id, log_json, _now()),
        )

    def add_chat(
        self,
        user_id: int,
        lesson_id: str,
        role: str,
        content: str,
        ceiling: str | None,
        citations_json: str | None,
    ) -> int:
        return self._write(
            "INSERT INTO chats (user_id, lesson_id, role, content, ceiling, citations_json,"
            " created_at) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (user_id, lesson_id, role, content, ceiling, citations_json, _now()),
        )

    def chat_history(self, user_id: int, lesson_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """The newest `limit` messages, oldest first."""
        return self._all(
            "SELECT * FROM (SELECT * FROM chats WHERE user_id = %s AND lesson_id = %s"
            " ORDER BY id DESC LIMIT %s) AS recent ORDER BY id",
            (user_id, lesson_id, limit),
        )

    def add_check(self, user_id: int, lesson_id: str, passed: bool, output: str) -> int:
        return self._write(
            "INSERT INTO checks (user_id, lesson_id, passed, output, created_at)"
            " VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user_id, lesson_id, passed, output, _now()),
        )

    def last_check(self, user_id: int, lesson_id: str) -> dict[str, Any] | None:
        return self._one(
            "SELECT * FROM checks WHERE user_id = %s AND lesson_id = %s ORDER BY id DESC LIMIT 1",
            (user_id, lesson_id),
        )

    def set_mastery(self, user_id: int, lesson_id: str, state: str) -> None:
        self._all(
            "INSERT INTO mastery (user_id, lesson_id, state, updated_at) VALUES (%s, %s, %s, %s)"
            " ON CONFLICT (user_id, lesson_id) DO UPDATE SET state = excluded.state,"
            " updated_at = excluded.updated_at",
            (user_id, lesson_id, state, _now()),
        )

    def mastery_for(self, user_id: int) -> dict[str, str]:
        rows = self._all("SELECT lesson_id, state FROM mastery WHERE user_id = %s", (user_id,))
        return {r["lesson_id"]: r["state"] for r in rows}

    def log_event(self, user_id: int, kind: str, data_json: str) -> int:
        return self._write(
            "INSERT INTO events (user_id, kind, data_json, created_at)"
            " VALUES (%s, %s, %s, %s) RETURNING id",
            (user_id, kind, data_json, _now()),
        )

    def events_for(
        self, user_id: int, kind: str, lesson_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Events of one kind; lesson_id filters on the "lesson_id" key inside data_json."""
        if lesson_id is None:
            return self._all(
                "SELECT * FROM events WHERE user_id = %s AND kind = %s ORDER BY id",
                (user_id, kind),
            )
        return self._all(
            "SELECT * FROM events WHERE user_id = %s AND kind = %s"
            " AND data_json::jsonb ->> 'lesson_id' = %s ORDER BY id",
            (user_id, kind, lesson_id),
        )

    def close(self) -> None:
        self.conn.close()


def open_pg_store(url: str) -> PostgresStore:
    return PostgresStore(connect_pg(url))
