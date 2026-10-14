"""SPEC section 23 row: Tutor."""

import pytest
from fastapi.testclient import TestClient

from app.content import Lesson
from app.main import app

from .conftest import ALL, sse


def chat(client: TestClient, lesson: Lesson, active_item: str | None = None) -> tuple[str, dict]:
    r = client.post(f"/api/tutor/{lesson.id}", json={"message": "help", "active_item": active_item})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    return r.text, sse(r.text)


@pytest.mark.parametrize("lesson", ALL)
def test_early_reply_has_valid_citations_and_no_code(client: TestClient, lesson: Lesson) -> None:
    raw, ev = chat(client, lesson)  # no attempts yet, so the ceiling is L1
    assert "event: html" in raw and ev["ceiling"] == "L1"
    assert "event: token" not in raw  # below L4 only the filtered html is sent
    assert "<pre" not in ev["html"] and "x = 1" not in raw
    assert [c["id"] for c in ev["citations"]] == [lesson.sections[0].id]
    assert "bogus" not in ev["html"]  # the invalid [§bogus] marker is dropped


@pytest.mark.parametrize("lesson", ALL)
def test_history_survives_a_new_client(client: TestClient, lesson: Lesson) -> None:
    chat(client, lesson)
    with TestClient(app) as fresh:  # same DB, like a page refresh after a restart
        turns = fresh.get(f"/api/tutor/{lesson.id}/history").json()
    assert [t["role"] for t in turns] == ["user", "assistant"]
    assert turns[0]["text"] == "help" and turns[1]["ceiling"] == "L1"


@pytest.mark.parametrize("lesson", ALL)
def test_reveal_logs_an_event_and_lifts_the_ceiling(
    client: TestClient, store, uid: int, lesson: Lesson
) -> None:
    item = lesson.quiz[0]
    assert client.post(f"/api/tutor/{lesson.id}/reveal", json={"item_id": item.id}).json()["answer"]
    assert len(store.events_for(uid, "reveal", lesson.id)) == 1
    raw, ev = chat(client, lesson)
    assert ev["ceiling"] == "L6" and "<pre" in ev["html"]  # code allowed now
    assert "event: token" in raw  # and tokens stream from L4 up


@pytest.mark.parametrize("lesson", ALL)
def test_active_quiz_item_caps_the_ceiling_at_l2(client: TestClient, lesson: Lesson) -> None:
    item = lesson.quiz[0]
    client.post(f"/api/tutor/{lesson.id}/reveal", json={"item_id": item.id})  # even after a reveal
    raw, ev = chat(client, lesson, active_item=item.id)
    assert ev["ceiling"] == "L2" and "<pre" not in ev["html"] and "event: token" not in raw
