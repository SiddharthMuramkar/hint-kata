import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.content import load_lessons
from app.main import app
from app.mastery import compute_state, log_config, refresh
from app.store import SqliteStore, open_store

FIXTURES = Path(__file__).parent / "fixtures" / "content"
LESSONS = load_lessons(FIXTURES)
LESSON = LESSONS["fx-demo"]
NOW = datetime(2026, 6, 1, tzinfo=UTC)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[SqliteStore]:
    s = open_store(tmp_path / "t.db")
    yield s
    s.close()


def attempt(
    s: SqliteStore, item: str, day: str, kind: str = "quiz", correct: bool = True, try_no: int = 1
) -> None:
    """Add an attempt, then backdate it to `day` (YYYY-MM-DD)."""
    uid = s.ensure_user("owner")
    row_id = s.add_attempt(uid, "fx-demo", item, kind, "{}", correct, "sure", try_no, 1000)
    s.conn.execute(
        "UPDATE attempts SET created_at = ? WHERE id = ?", (f"{day}T09:00:00+00:00", row_id)
    )
    s.conn.commit()


def state(s: SqliteStore) -> str:
    return compute_state(s, LESSON, s.ensure_user("owner"), NOW)


def master(s: SqliteStore, passed: bool = True) -> None:
    """Everything right on day one, recalled in review on day two, check done."""
    for item in ("q1", "q2", "q3"):
        attempt(s, item, "2026-05-01")
        attempt(s, item, "2026-05-02", kind="review")
    s.add_check(s.ensure_user("owner"), "fx-demo", passed, "out")


def test_notstarted_with_no_data(store: SqliteStore) -> None:
    assert state(store) == "notstarted"


def test_learning_after_one_attempt(store: SqliteStore) -> None:
    attempt(store, "q1", "2026-05-01", correct=False)
    assert state(store) == "learning"


def test_a_chat_alone_starts_the_lesson(store: SqliteStore) -> None:
    store.add_chat(store.ensure_user("owner"), "fx-demo", "user", "hi", None, None)
    assert state(store) == "learning"


def test_mastered_path(store: SqliteStore) -> None:
    master(store)
    assert state(store) == "mastered"


def test_one_day_of_recall_is_not_enough(store: SqliteStore) -> None:
    for item in ("q1", "q2", "q3"):
        attempt(store, item, "2026-05-01")
    store.add_check(store.ensure_user("owner"), "fx-demo", True, "out")
    assert state(store) == "learning"


def test_reveal_disqualifies_that_day(store: SqliteStore) -> None:
    master(store)
    uid = store.ensure_user("owner")
    store.log_event(uid, "reveal", json.dumps({"lesson_id": "fx-demo"}))
    store.conn.execute("UPDATE events SET created_at = '2026-05-02T10:00:00+00:00'")
    store.conn.commit()
    assert state(store) == "learning"


def test_failed_last_check_blocks_mastery(store: SqliteStore) -> None:
    master(store)
    store.add_check(store.ensure_user("owner"), "fx-demo", False, "boom")
    assert state(store) == "learning"


def test_hinted_or_second_try_answers_do_not_count(store: SqliteStore) -> None:
    master(store)
    store.conn.execute("UPDATE attempts SET try_no = 2 WHERE item_id = 'q3'")
    store.conn.commit()
    assert state(store) == "learning"


def test_thresholds_come_from_settings(store: SqliteStore, monkeypatch: pytest.MonkeyPatch) -> None:
    master(store)
    assert state(store) == "mastered"
    monkeypatch.setattr(settings, "mastery_recalls_required", 3)
    assert state(store) == "learning"
    monkeypatch.setattr(settings, "mastery_recalls_required", 1)
    monkeypatch.setattr(settings, "mastery_quiz_threshold", 1.1)
    assert state(store) == "learning"


def test_refresh_logs_each_transition_once(store: SqliteStore) -> None:
    uid = store.ensure_user("owner")

    def changes() -> list[dict[str, str]]:
        return [json.loads(e["data_json"]) for e in store.events_for(uid, "mastery_changed")]

    assert refresh(store, LESSONS, uid)["fx-demo"] == "notstarted"
    assert changes() == []
    attempt(store, "q1", "2026-05-01", correct=False)
    refresh(store, LESSONS, uid)
    refresh(store, LESSONS, uid)
    master(store)
    assert refresh(store, LESSONS, uid)["fx-demo"] == "mastered"
    refresh(store, LESSONS, uid)
    assert changes() == [
        {"lesson_id": "fx-demo", "from": "notstarted", "to": "learning"},
        {"lesson_id": "fx-demo", "from": "learning", "to": "mastered"},
    ]
    assert store.mastery_for(uid)["fx-demo"] == "mastered"


def test_config_logged_only_when_it_changes(
    store: SqliteStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    uid = store.ensure_user("owner")
    log_config(store, uid)
    log_config(store, uid)
    assert len(store.events_for(uid, "mastery_config")) == 1
    monkeypatch.setattr(settings, "mastery_quiz_threshold", 0.9)
    log_config(store, uid)
    events = store.events_for(uid, "mastery_config")
    assert json.loads(events[-1]["data_json"]) == {"quiz_threshold": 0.9, "recalls_required": 2}


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "content_root", str(FIXTURES))
    monkeypatch.setattr(settings, "hintkata_db_path", str(tmp_path / "t.db"))
    with TestClient(app) as c:
        yield c


def test_home_shows_badges_and_startup_logged_config(client: TestClient) -> None:
    s = open_store(settings.hintkata_db_path)
    uid = s.ensure_user("owner")
    assert len(s.events_for(uid, "mastery_config")) == 1
    assert 'class="badge notstarted">Not started' in client.get("/").text
    s.add_attempt(uid, "fx-demo", "q1", "quiz", "0", False, "sure", 1, 1000)
    s.close()
    assert 'class="badge learning">Learning' in client.get("/").text


def test_api_progress_shape(client: TestClient) -> None:
    body = client.get("/api/progress").json()
    assert body == {"mastery": {"fx-demo": "notstarted"}, "due": 0}
