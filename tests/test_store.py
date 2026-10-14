import json
import sqlite3
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.store import SqliteStore, Store, open_store


@pytest.fixture
def store(tmp_path: Path) -> Iterator[SqliteStore]:
    s = open_store(tmp_path / "sub" / "t.db")  # parent dir is created
    yield s
    s.close()


@pytest.fixture
def uid(store: SqliteStore) -> int:
    return store.ensure_user("ada")


def test_schema_pragmas_and_version(store: SqliteStore) -> None:
    tables = {
        r["name"] for r in store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    expected = {
        "users", "attempts", "grades", "cards", "review_logs", "chats", "checks",
        "mastery", "events", "schema_version",
    }  # fmt: skip
    assert expected <= tables
    assert store.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert store.conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert [r[0] for r in store.conn.execute("SELECT version FROM schema_version")] == [1]


def test_reopen_keeps_single_version(tmp_path: Path) -> None:
    path = tmp_path / "t.db"
    open_store(path).close()
    s = open_store(path)
    assert s.conn.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 1
    s.close()


def test_foreign_keys_enforced(store: SqliteStore) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        store.add_check(999, "l1", True, "out")


def test_ensure_user_idempotent(store: SqliteStore) -> None:
    assert store.ensure_user("ada") == store.ensure_user("ada")
    assert store.ensure_user("bob") != store.ensure_user("ada")


def test_attempts(store: SqliteStore, uid: int) -> None:
    store.add_attempt(uid, "l1", "q1", "quiz", "a", True, "sure", 1, 1200)
    store.add_attempt(uid, "l2", "q1", "quiz", "b", False, "guessing", 1, 10)
    rows = store.attempts_for(uid, "l1")
    assert len(rows) == 1
    assert rows[0]["correct"] == 1 and rows[0]["confidence"] == "sure"
    assert rows[0]["elapsed_ms"] == 1200


def test_grades(store: SqliteStore, uid: int) -> None:
    store.add_grade(uid, "l1", "d1", 1, "ans", json.dumps({"met": []}), False)
    store.add_grade(uid, "l1", "d1", 2, "ans2", "{}", True)
    rows = store.grades_for(uid, "l1", "d1")
    assert [r["attempt_no"] for r in rows] == [1, 2]
    assert [r["flagged"] for r in rows] == [0, 1]
    assert store.grades_for(uid, "l1", "other") == []


def test_cards_upsert_get_review_log(store: SqliteStore, uid: int) -> None:
    assert store.get_card(uid, "k") is None
    cid = store.upsert_card(uid, "k", "l1", '{"v": 1}', "2026-01-01T00:00:00+00:00", None)
    cid2 = store.upsert_card(uid, "k", "l1", '{"v": 2}', "2026-02-01T00:00:00+00:00", 3)
    assert cid == cid2
    card = store.get_card(uid, "k")
    assert card is not None
    assert card["card_json"] == '{"v": 2}' and card["last_rating"] == 3
    assert card["due"] == "2026-02-01T00:00:00+00:00"
    assert store.add_review_log(cid, "{}") > 0
    assert store.conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0] == 1


def test_due_cards_only_due_and_ordered(store: SqliteStore, uid: int) -> None:
    now = datetime(2026, 6, 1, tzinfo=UTC)
    for key, delta in [("late", -1), ("early", -5), ("future", 3)]:
        due = (now + timedelta(days=delta)).isoformat()
        store.upsert_card(uid, key, "l1", "{}", due, None)
    got = store.due_cards(uid, now.isoformat())
    assert [c["item_key"] for c in got] == ["early", "late"]
    assert len(store.due_cards(uid, now.isoformat(), limit=1)) == 1


def test_chats(store: SqliteStore, uid: int) -> None:
    for i in range(5):
        store.add_chat(uid, "l1", "user" if i % 2 == 0 else "assistant", f"m{i}", "L1", None)
    store.add_chat(uid, "l2", "user", "other", None, '["s1"]')
    assert [c["content"] for c in store.chat_history(uid, "l1")] == [f"m{i}" for i in range(5)]
    assert [c["content"] for c in store.chat_history(uid, "l1", limit=2)] == ["m3", "m4"]
    assert store.chat_history(uid, "l2")[0]["citations_json"] == '["s1"]'


def test_checks(store: SqliteStore, uid: int) -> None:
    assert store.last_check(uid, "l1") is None
    store.add_check(uid, "l1", False, "fail")
    store.add_check(uid, "l1", True, "ok")
    last = store.last_check(uid, "l1")
    assert last is not None and last["passed"] == 1 and last["output"] == "ok"


def test_mastery(store: SqliteStore, uid: int) -> None:
    assert store.mastery_for(uid) == {}
    store.set_mastery(uid, "l1", "learning")
    store.set_mastery(uid, "l2", "learning")
    store.set_mastery(uid, "l1", "mastered")
    assert store.mastery_for(uid) == {"l1": "mastered", "l2": "learning"}


def test_events(store: SqliteStore, uid: int) -> None:
    store.log_event(uid, "reveal", json.dumps({"lesson_id": "l1", "item": "q1"}))
    store.log_event(uid, "reveal", json.dumps({"lesson_id": "l2"}))
    store.log_event(uid, "surprise", json.dumps({"lesson_id": "l1"}))
    assert len(store.events_for(uid, "reveal")) == 2
    only = store.events_for(uid, "reveal", lesson_id="l1")
    assert len(only) == 1 and json.loads(only[0]["data_json"])["item"] == "q1"


def test_usable_from_another_thread(store: SqliteStore, uid: int) -> None:
    result: list[int] = []
    errors: list[BaseException] = []

    def work() -> None:
        try:
            result.append(store.add_check(uid, "l1", True, "from thread"))
        except BaseException as e:  # noqa: BLE001
            errors.append(e)

    t = threading.Thread(target=work)
    t.start()
    t.join()
    assert not errors and result


def test_sqlite_store_is_a_store(store: SqliteStore) -> None:
    s: Store = store  # ty verifies the Protocol is satisfied
    assert s is store
