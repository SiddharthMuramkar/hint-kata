import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fsrs import Rating

from app.config import settings
from app.content import load_lessons
from app.main import app
from app.quiz import grade_item
from app.review import (
    criterion_item_id,
    due_items,
    item_key,
    rating_for,
    record_criterion,
    record_quiz_attempt,
    record_result,
)
from app.store import SqliteStore, open_store

FIXTURES = Path(__file__).parent / "fixtures" / "content"
LESSONS = load_lessons(FIXTURES)
Q1 = LESSONS["fx-demo"].quiz[0]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.fixture
def store(tmp_path: Path) -> Iterator[SqliteStore]:
    s = open_store(tmp_path / "t.db")
    yield s
    s.close()


@pytest.mark.parametrize(
    ("correct", "confidence", "try_no", "hint", "ms", "expected"),
    [
        (False, "sure", 1, False, 1000, Rating.Again),
        (False, "guessing", 2, True, 99999, Rating.Again),
        (True, "sure", 2, False, 1000, Rating.Hard),
        (True, "sure", 1, True, 1000, Rating.Hard),
        (True, "guessing", 1, False, 1000, Rating.Hard),
        (True, "thinkso", 1, False, 1000, Rating.Good),
        (True, "sure", 1, False, 20_000, Rating.Good),
        (True, "sure", 1, False, 9_999, Rating.Easy),
        (True, "sure", 1, False, 10_000, Rating.Good),
        (True, "thinkso", 1, False, 1000, Rating.Good),
    ],
)
def test_rating_for(
    correct: bool, confidence: str, try_no: int, hint: bool, ms: int, expected: Rating
) -> None:
    assert rating_for(correct, confidence, try_no, hint, ms) == expected


def test_record_result_creates_then_reschedules(store: SqliteStore) -> None:
    uid = store.ensure_user("u")
    first = record_result(store, uid, "fx-demo", "q1", Rating.Again, NOW)
    card = store.get_card(uid, item_key("fx-demo", "q1"))
    assert card is not None
    assert (card["due"], card["last_rating"]) == (first, 1)
    assert datetime.fromisoformat(first) > NOW
    later = NOW + timedelta(days=1)
    second = record_result(store, uid, "fx-demo", "q1", Rating.Good, later)
    again = store.get_card(uid, item_key("fx-demo", "q1"))
    assert again is not None
    assert (again["id"], again["last_rating"]) == (card["id"], 3)
    assert datetime.fromisoformat(second) > later
    assert second != first
    logs = store.conn.execute("SELECT COUNT(*) FROM review_logs").fetchone()[0]
    assert logs == 2


def test_surprise_caps_due_at_one_day(store: SqliteStore) -> None:
    uid = store.ensure_user("u")
    plain = record_result(store, uid, "fx-demo", "q1", Rating.Easy, NOW)
    assert datetime.fromisoformat(plain) > NOW + timedelta(days=1)
    capped = record_result(store, uid, "fx-demo", "q2", Rating.Easy, NOW, surprise=True)
    assert datetime.fromisoformat(capped) == NOW + timedelta(days=1)


def test_quiz_attempt_hook_only_makes_cards_for_misses(store: SqliteStore) -> None:
    uid = store.ensure_user("u")
    right, wrong = grade_item(Q1, 0), grade_item(Q1, 1)
    assert record_quiz_attempt(store, uid, "fx-demo", Q1, right, "sure", 1, 10) is None
    assert store.get_card(uid, item_key("fx-demo", "q1")) is None
    assert record_quiz_attempt(store, uid, "fx-demo", Q1, wrong, "sure", 1, 10) is not None
    assert record_quiz_attempt(store, uid, "fx-demo", Q1, wrong, "sure", 2, 10) is None
    assert record_quiz_attempt(store, uid, "fx-demo", Q1, right, "sure", 2, 10) is not None
    card = store.get_card(uid, item_key("fx-demo", "q1"))
    assert card is not None
    assert card["last_rating"] == 2  # Hard: right on the second try


def test_record_criterion(store: SqliteStore) -> None:
    uid = store.ensure_user("u")
    assert record_criterion(store, uid, "fx-demo", "d1", "reuse", True) is None  # no card yet
    assert record_criterion(store, uid, "fx-demo", "d1", "reuse", False) is not None
    card = store.get_card(uid, item_key("fx-demo", criterion_item_id("d1", "reuse")))
    assert card is not None
    assert card["last_rating"] == 1
    record_criterion(store, uid, "fx-demo", "d1", "reuse", True)
    card = store.get_card(uid, item_key("fx-demo", "d1#reuse"))
    assert card is not None
    assert card["last_rating"] == 3


def test_due_items_filters_orders_and_skips_unknown(store: SqliteStore) -> None:
    uid = store.ensure_user("u")
    past = NOW - timedelta(days=2)
    record_result(store, uid, "fx-demo", "q2", Rating.Again, past)
    record_result(store, uid, "fx-demo", "q1", Rating.Again, past - timedelta(hours=1))
    record_result(store, uid, "fx-demo", "gone", Rating.Again, past)
    record_result(store, uid, "no-lesson", "q1", Rating.Again, past)
    record_result(store, uid, "fx-demo", "q3", Rating.Easy, NOW)  # not due yet
    record_criterion(store, uid, "fx-demo", "d1", "tests", False, NOW)
    due = due_items(store, LESSONS, uid, NOW)
    assert [d.item_id for d in due] == ["q1", "q2"]
    assert (due[0].kind, due[0].item, due[0].lesson_title) == ("quiz", Q1, "Demo lesson")
    later = due_items(store, LESSONS, uid, NOW + timedelta(days=30))
    crit = next(d for d in later if d.kind == "criterion")
    assert (crit.item_id, crit.item, crit.prompt) == ("d1#tests", None, "Why use dependencies?")
    assert crit.criterion_text == "Mentions overrides"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "content_root", str(FIXTURES))
    monkeypatch.setattr(settings, "hintkata_db_path", str(tmp_path / "t.db"))
    with TestClient(app) as c:
        yield c


def seed(rating: Rating, item_id: str = "q1") -> int:
    """Put an overdue card in the app's DB; return its id."""
    s = open_store(settings.hintkata_db_path)
    uid = s.ensure_user("owner")
    record_result(s, uid, "fx-demo", item_id, rating, datetime.now(UTC) - timedelta(days=3))
    card = s.get_card(uid, item_key("fx-demo", item_id))
    s.close()
    assert card is not None
    return card["id"]


def post(c: TestClient, item: str, answer: object, confidence: str = "sure") -> dict[str, object]:
    r = c.post(
        f"/api/quiz/fx-demo/{item}",
        json={"answer": answer, "confidence": confidence, "try_no": 1, "elapsed_ms": 5},
    )
    return r.json()


def test_quiz_post_returns_card_due_only_after_a_miss(client: TestClient) -> None:
    assert post(client, "q1", 0)["card_due"] is None
    miss = post(client, "q2", [0, 1, 2])
    assert miss["correct"] is False
    assert datetime.fromisoformat(str(miss["card_due"])).tzinfo is not None


def test_today_page_and_api_list_due_items(client: TestClient) -> None:
    assert "Nothing is due" in client.get("/today").text
    seed(Rating.Again, "q1")
    seed(Rating.Again, "d1#reuse")
    page = client.get("/today").text
    assert "What is a dependency?" in page
    assert "Demo lesson" in page
    assert 'href="/lessons/fx-demo"' in page
    assert "Mentions reuse" in page
    assert "Today (2 due)" in client.get("/").text
    body = client.get("/api/review")
    items = body.json()
    assert {i["item_id"] for i in items} == {"q1", "d1#reuse"}
    for banned in ('"correct"', "feedback", "misconception", '"answer"'):
        assert banned not in body.text


def test_post_review_updates_due(client: TestClient) -> None:
    cid = seed(Rating.Again, "q1")
    r = client.post(
        f"/api/review/{cid}", json={"answer": 0, "confidence": "sure", "elapsed_ms": 50}
    )
    assert r.status_code == 200
    out = r.json()
    assert out["correct"] is True
    assert datetime.fromisoformat(out["next_due"]) > datetime.now(UTC)
    assert client.get("/api/review").json() == []
    s = open_store(settings.hintkata_db_path)
    attempts = s.attempts_for(s.ensure_user("owner"), "fx-demo")
    s.close()
    assert [(a["kind"], a["item_id"], json.loads(a["answer"])) for a in attempts] == [
        ("review", "q1", 0)
    ]


def test_post_review_wrong_surprise_and_criterion(client: TestClient) -> None:
    cid = seed(Rating.Good, "q1")
    wrong = client.post(f"/api/review/{cid}", json={"answer": 1, "confidence": "sure"}).json()
    assert wrong["correct"] is False
    assert wrong["feedback"] == "No decorator is needed."
    assert datetime.fromisoformat(wrong["next_due"]) <= datetime.now(UTC) + timedelta(days=1)
    crit = seed(Rating.Again, "d1#scope")
    ok = client.post(f"/api/review/{crit}", json={"self_rating": "good"})
    assert ok.json()["correct"] is True
    assert client.post(f"/api/review/{crit}", json={}).status_code == 422
    assert client.post(f"/api/review/{cid}", json={}).status_code == 422
    assert client.post("/api/review/99999", json={"answer": 0}).status_code == 404
