from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.content import QuizItem, load_lessons
from app.main import app
from app.quiz import grade_item, score, scramble
from app.store import open_store

FIXTURES = Path(__file__).parent / "fixtures" / "content"
ITEMS = {q.id: q for q in load_lessons(FIXTURES)["fx-demo"].quiz}
RIGHT_ORDER = [scramble(ITEMS["q2"]).index(i) for i in range(3)]


def blank(answer: str) -> QuizItem:
    return ITEMS["q3"].model_copy(update={"answer": answer})


def test_single() -> None:
    right = grade_item(ITEMS["q1"], 0)
    assert (right.correct, right.feedback, right.correct_answer) == (True, "Right.", 0)
    wrong = grade_item(ITEMS["q1"], 1)
    assert not wrong.correct
    assert wrong.feedback == "No decorator is needed."
    assert wrong.misconception == "Dependencies need decorators."
    assert not grade_item(ITEMS["q1"], 9).correct
    assert not grade_item(ITEMS["q1"], "0").correct


def test_scramble_is_deterministic_and_never_the_answer() -> None:
    item = ITEMS["q2"]
    assert scramble(item) == scramble(item)
    assert sorted(scramble(item)) == [0, 1, 2]
    assert scramble(item) != [0, 1, 2]


def test_order() -> None:
    item = ITEMS["q2"]
    shown = scramble(item)
    right = [shown.index(i) for i in range(3)]  # positions, in true order
    r = grade_item(item, right)
    assert r.correct
    assert r.correct_answer == right
    assert not grade_item(item, [0, 1, 2]).correct  # the shown order is never right
    assert not grade_item(item, [0, 0, 0]).correct
    assert not grade_item(item, "nope").correct


def test_blank_normalises_and_supports_regex() -> None:
    assert grade_item(ITEMS["q3"], "  depends ").correct
    assert grade_item(blank("a  b"), "A B").correct
    assert not grade_item(ITEMS["q3"], "Depend").correct
    assert not grade_item(ITEMS["q3"], 3).correct
    rx = blank(r"re:Depends|Security")
    assert grade_item(rx, "security").correct
    assert not grade_item(rx, "Security(x)").correct  # fullmatch, not search
    assert grade_item(ITEMS["q3"], "Depends").explanation == "Depends wraps the callable."


def test_score_counts_first_try_only() -> None:
    items = list(ITEMS.values())
    attempts = [
        {"item_id": "q1", "try_no": 1, "correct": 1},
        {"item_id": "q2", "try_no": 1, "correct": 0},
        {"item_id": "q2", "try_no": 2, "correct": 1},
    ]
    assert score(attempts, items) == pytest.approx(1 / 3)
    assert score([], items) == 0.0
    assert score(attempts, []) == 0.0


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "content_root", str(FIXTURES))
    monkeypatch.setattr(settings, "hintkata_db_path", str(tmp_path / "t.db"))
    with TestClient(app) as c:
        yield c


def post(
    c: TestClient, item: str, answer: object, try_no: int = 1, confidence: str = "thinkso"
) -> dict[str, object]:
    r = c.post(
        f"/api/quiz/fx-demo/{item}",
        json={"answer": answer, "confidence": confidence, "try_no": try_no, "elapsed_ms": 5},
    )
    return {"status": r.status_code, **r.json()}


def test_correct_first_try(client: TestClient) -> None:
    r = post(client, "q1", 0)
    assert r["correct"] is True
    assert r["correct_answer"] == 0
    assert r["surprise"] is False
    assert r["score"] == pytest.approx(1 / 3)
    assert r["done"] is False


def test_wrong_then_second_try_then_third_rejected(client: TestClient) -> None:
    r = post(client, "q1", 1)
    assert (r["correct"], r["correct_answer"]) == (False, None)
    assert r["misconception"] == "Dependencies need decorators."
    r = post(client, "q1", 1, try_no=2)
    assert (r["status"], r["correct"], r["correct_answer"]) == (200, False, 0)
    assert post(client, "q1", 0, try_no=2)["status"] == 409  # already used
    assert post(client, "q1", 0, try_no=3)["status"] == 409
    assert post(client, "q1", 0, try_no=1)["status"] == 409
    assert post(client, "q2", 0, try_no=2)["status"] == 409  # no wrong first try
    attempts = client.get("/api/quiz/fx-demo").json()
    assert attempts["score"] == 0
    assert attempts["items"][0]["correct_first_try"] is False


def test_surprise_and_done(client: TestClient) -> None:
    assert post(client, "q1", 1, confidence="sure")["surprise"] is True
    assert post(client, "q1", 0, try_no=2, confidence="sure")["surprise"] is False
    post(client, "q2", RIGHT_ORDER)
    done = post(client, "q3", "depends")
    assert done["done"] is True
    assert done["score"] == pytest.approx(2 / 3)


def test_get_hides_answers(client: TestClient) -> None:
    body = client.get("/api/quiz/fx-demo")
    data = body.json()
    assert [i["id"] for i in data["items"]] == ["q1", "q2", "q3"]
    assert data["items"][0]["options"] == ["A function", "A class decorator"]
    shown = scramble(ITEMS["q2"])
    assert data["items"][1]["steps"] == [ITEMS["q2"].steps[i] for i in shown]
    assert data["items"][0]["answered"] is False
    assert data["items"][0]["correct_first_try"] is None
    for banned in ('"correct"', "feedback", "misconception", "Depends wraps", '"answer"'):
        assert banned not in body.text


def test_unknown_lesson_or_item_is_404(client: TestClient) -> None:
    assert post(client, "nope", 0)["status"] == 404
    assert client.get("/api/quiz/nope").status_code == 404
    r = client.post(
        "/api/quiz/nope/q1", json={"answer": 0, "confidence": "sure", "try_no": 1, "elapsed_ms": 1}
    )
    assert r.status_code == 404


def test_lesson_page_includes_quiz(client: TestClient) -> None:
    html = client.get("/lessons/fx-demo").text
    assert 'id="quiz"' in html
    assert "/static/js/quiz.js" in html


def test_only_quiz_attempts_count(client: TestClient) -> None:
    store = open_store(settings.hintkata_db_path)
    store.add_attempt(
        store.ensure_user("owner"), "fx-demo", "q1", "review", "0", True, "sure", 1, 1
    )
    store.close()
    data = client.get("/api/quiz/fx-demo").json()
    assert data["score"] == 0
    assert data["items"][0]["answered"] is False
    assert post(client, "q1", 0)["status"] == 200  # the review attempt did not use up try 1


def test_wrong_first_try_survives_reload(client: TestClient) -> None:
    post(client, "q1", 1)
    first = client.get("/api/quiz/fx-demo").json()["items"][0]
    assert (first["answered"], first["can_retry"]) == (True, True)
    post(client, "q2", RIGHT_ORDER, confidence="guessing")
    post(client, "q3", "depends")
    assert post(client, "q3", "x", try_no=1)["status"] == 409
    assert client.get("/api/quiz/fx-demo").json()["items"][0]["can_retry"] is True
    assert post(client, "q1", 0, try_no=2)["done"] is True
    assert client.get("/api/quiz/fx-demo").json()["items"][0]["can_retry"] is False


def test_attempt_is_persisted(client: TestClient) -> None:
    post(client, "q1", 1, confidence="guessing")
    store = open_store(settings.hintkata_db_path)
    (row,) = store.attempts_for(store.ensure_user("owner"), "fx-demo")
    store.close()
    assert (row["kind"], row["item_id"], row["answer"], row["correct"]) == ("quiz", "q1", "1", 0)
    assert (row["confidence"], row["try_no"], row["elapsed_ms"]) == ("guessing", 1, 5)
