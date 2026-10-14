"""Persistence. All SQL lives in SqliteStore so a PostgresStore can drop in later."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

SCHEMA = Path(__file__).with_name("schema.sql")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def connect(path: str | Path) -> sqlite3.Connection:
    """Open the DB. PRAGMAs run while autocommit is on, because SQLite ignores
    foreign_keys inside a transaction and refuses a journal_mode change in one."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, autocommit=True, check_same_thread=False, timeout=5.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA.read_text())
    if conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 0:
        conn.execute("INSERT INTO schema_version (version) VALUES (1)")
    conn.autocommit = False
    conn.row_factory = sqlite3.Row
    return conn


class Store(Protocol):
    def ensure_user(self, name: str) -> int: ...
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
    ) -> int: ...
    def attempts_for(self, user_id: int, lesson_id: str) -> list[dict[str, Any]]: ...
    def add_grade(
        self,
        user_id: int,
        lesson_id: str,
        question_id: str,
        attempt_no: int,
        answer: str,
        result_json: str,
        flagged: bool,
    ) -> int: ...
    def grades_for(
        self, user_id: int, lesson_id: str, question_id: str
    ) -> list[dict[str, Any]]: ...
    def upsert_card(
        self,
        user_id: int,
        item_key: str,
        lesson_id: str,
        card_json: str,
        due: str,
        last_rating: int | None,
    ) -> int: ...
    def get_card(self, user_id: int, item_key: str) -> dict[str, Any] | None: ...
    def due_cards(self, user_id: int, now_iso: str, limit: int = 20) -> list[dict[str, Any]]: ...
    def add_review_log(self, card_id: int, log_json: str) -> int: ...
    def add_chat(
        self,
        user_id: int,
        lesson_id: str,
        role: str,
        content: str,
        ceiling: str | None,
        citations_json: str | None,
    ) -> int: ...
    def chat_history(
        self, user_id: int, lesson_id: str, limit: int = 50
    ) -> list[dict[str, Any]]: ...
    def add_check(self, user_id: int, lesson_id: str, passed: bool, output: str) -> int: ...
    def last_check(self, user_id: int, lesson_id: str) -> dict[str, Any] | None: ...
    def set_mastery(self, user_id: int, lesson_id: str, state: str) -> None: ...
    def mastery_for(self, user_id: int) -> dict[str, str]: ...
    def log_event(self, user_id: int, kind: str, data_json: str) -> int: ...
    def events_for(
        self, user_id: int, kind: str, lesson_id: str | None = None
    ) -> list[dict[str, Any]]: ...
    def close(self) -> None: ...


class SqliteStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _write(self, sql: str, params: tuple[Any, ...]) -> int:
        """Run one write, commit, return the row id of the insert."""
        try:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
        except BaseException:
            self.conn.rollback()
            raise
        return cur.lastrowid or 0

    def _all(self, sql: str, params: tuple[Any, ...]) -> list[dict[str, Any]]:
        rows = self.conn.execute(sql, params).fetchall()
        # release the read snapshot; sqlite3 reopens a deferred transaction at once
        self.conn.rollback()
        return [dict(r) for r in rows]

    def _one(self, sql: str, params: tuple[Any, ...]) -> dict[str, Any] | None:
        rows = self._all(sql, params)
        return rows[0] if rows else None

    def ensure_user(self, name: str) -> int:
        self._write("INSERT OR IGNORE INTO users (name, created_at) VALUES (?, ?)", (name, _now()))
        row = self._one("SELECT id FROM users WHERE name = ?", (name,))
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
            " confidence, try_no, elapsed_ms, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                lesson_id,
                item_id,
                kind,
                answer,
                int(correct),
                confidence,
                try_no,
                elapsed_ms,
                _now(),
            ),
        )

    def attempts_for(self, user_id: int, lesson_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM attempts WHERE user_id = ? AND lesson_id = ? ORDER BY id",
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
            " result_json, flagged, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                lesson_id,
                question_id,
                attempt_no,
                answer,
                result_json,
                int(flagged),
                _now(),
            ),
        )

    def grades_for(self, user_id: int, lesson_id: str, question_id: str) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM grades WHERE user_id = ? AND lesson_id = ? AND question_id = ?"
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
        self._write(
            "INSERT INTO cards (user_id, item_key, lesson_id, card_json, due, last_rating,"
            " updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (user_id, item_key) DO UPDATE SET lesson_id = excluded.lesson_id,"
            " card_json = excluded.card_json, due = excluded.due,"
            " last_rating = excluded.last_rating, updated_at = excluded.updated_at",
            (user_id, item_key, lesson_id, card_json, due, last_rating, _now()),
        )
        card = self.get_card(user_id, item_key)
        assert card is not None
        return card["id"]

    def get_card(self, user_id: int, item_key: str) -> dict[str, Any] | None:
        return self._one(
            "SELECT * FROM cards WHERE user_id = ? AND item_key = ?", (user_id, item_key)
        )

    def due_cards(self, user_id: int, now_iso: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._all(
            "SELECT * FROM cards WHERE user_id = ? AND due <= ? ORDER BY due, id LIMIT ?",
            (user_id, now_iso, limit),
        )

    def add_review_log(self, card_id: int, log_json: str) -> int:
        return self._write(
            "INSERT INTO review_logs (card_id, log_json, created_at) VALUES (?, ?, ?)",
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
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, lesson_id, role, content, ceiling, citations_json, _now()),
        )

    def chat_history(self, user_id: int, lesson_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """The newest `limit` messages, oldest first."""
        return self._all(
            "SELECT * FROM (SELECT * FROM chats WHERE user_id = ? AND lesson_id = ?"
            " ORDER BY id DESC LIMIT ?) ORDER BY id",
            (user_id, lesson_id, limit),
        )

    def add_check(self, user_id: int, lesson_id: str, passed: bool, output: str) -> int:
        return self._write(
            "INSERT INTO checks (user_id, lesson_id, passed, output, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, lesson_id, int(passed), output, _now()),
        )

    def last_check(self, user_id: int, lesson_id: str) -> dict[str, Any] | None:
        return self._one(
            "SELECT * FROM checks WHERE user_id = ? AND lesson_id = ? ORDER BY id DESC LIMIT 1",
            (user_id, lesson_id),
        )

    def set_mastery(self, user_id: int, lesson_id: str, state: str) -> None:
        self._write(
            "INSERT INTO mastery (user_id, lesson_id, state, updated_at) VALUES (?, ?, ?, ?)"
            " ON CONFLICT (user_id, lesson_id) DO UPDATE SET state = excluded.state,"
            " updated_at = excluded.updated_at",
            (user_id, lesson_id, state, _now()),
        )

    def mastery_for(self, user_id: int) -> dict[str, str]:
        rows = self._all("SELECT lesson_id, state FROM mastery WHERE user_id = ?", (user_id,))
        return {r["lesson_id"]: r["state"] for r in rows}

    def log_event(self, user_id: int, kind: str, data_json: str) -> int:
        return self._write(
            "INSERT INTO events (user_id, kind, data_json, created_at) VALUES (?, ?, ?, ?)",
            (user_id, kind, data_json, _now()),
        )

    def events_for(
        self, user_id: int, kind: str, lesson_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Events of one kind; lesson_id filters on the "lesson_id" key inside data_json."""
        if lesson_id is None:
            return self._all(
                "SELECT * FROM events WHERE user_id = ? AND kind = ? ORDER BY id", (user_id, kind)
            )
        return self._all(
            "SELECT * FROM events WHERE user_id = ? AND kind = ?"
            " AND json_extract(data_json, '$.lesson_id') = ? ORDER BY id",
            (user_id, kind, lesson_id),
        )

    def close(self) -> None:
        self.conn.close()


def open_store(path: str | Path) -> SqliteStore:
    return SqliteStore(connect(path))
