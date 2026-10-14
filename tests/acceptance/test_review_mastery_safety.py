"""SPEC section 23 rows: Review queue, Mastery, Safety."""

import subprocess
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.content import Lesson
from app.markdown import render_markdown
from app.store import SqliteStore

from .conftest import ALL, LESSONS, ROOT, lessons_with, post_quiz, right, singles, wrong

QUIZ = lessons_with("quiz")


@pytest.mark.parametrize("lesson", QUIZ)
def test_a_miss_makes_a_due_card_and_answering_reschedules_it(
    client: TestClient, store: SqliteStore, uid: int, lesson: Lesson
) -> None:
    a, b = singles(lesson)[:2]
    assert client.get("/api/review").json() == []  # nothing seen, nothing due
    post_quiz(client, lesson, b, right(b))  # a right first try makes no card
    post_quiz(client, lesson, a, wrong(a))
    store.conn.execute(
        "UPDATE cards SET due = ?", ((datetime.now(UTC) - timedelta(days=1)).isoformat(),)
    )
    store.conn.commit()

    due = client.get("/api/review").json()
    assert [d["item_id"] for d in due] == [a.id]
    assert "correct" not in str(due)  # the card never shows the answer
    assert lesson.title in client.get("/today").text

    r = client.post(
        f"/api/review/{due[0]['card_id']}", json={"answer": right(a), "confidence": "sure"}
    )
    assert r.json()["correct"] is True
    assert datetime.fromisoformat(r.json()["next_due"]) > datetime.now(UTC)
    assert client.get("/api/review").json() == []


def test_home_badges_and_progress_shape(client: TestClient) -> None:
    assert client.get("/").text.count('class="badge notstarted"') == len(LESSONS)
    body = client.get("/api/progress").json()
    assert body == {"mastery": dict.fromkeys(LESSONS, "notstarted"), "due": 0}


@pytest.mark.parametrize("lesson", ALL)
def test_mastery_follows_each_action_up_to_mastered(
    client: TestClient, store: SqliteStore, uid: int, lesson: Lesson
) -> None:
    item = singles(lesson)[0]
    post_quiz(client, lesson, item, wrong(item))
    assert client.get("/api/progress").json()["mastery"][lesson.id] == "learning"
    assert 'class="badge learning"' in client.get("/").text

    # The rule (SPEC 9): every item right first try on one day, recalled right on another day,
    # and the hands-on check passed. Insert that history with backdated dates.
    store.conn.execute("DELETE FROM attempts")
    for q in lesson.quiz:
        for kind in ("quiz", "review"):
            store.add_attempt(uid, lesson.id, q.id, kind, "{}", True, "thinkso", 1, 20_000)
    store.conn.execute(
        "UPDATE attempts SET created_at = '2026-05-01T09:00:00+00:00' WHERE kind='quiz'"
    )
    store.conn.execute(
        "UPDATE attempts SET created_at = '2026-05-02T09:00:00+00:00' WHERE kind='review'"
    )
    store.conn.commit()
    if lesson.task_kind:
        store.add_check(uid, lesson.id, True, "ok")
    assert client.get("/api/progress").json()["mastery"][lesson.id] == "mastered"
    assert 'class="badge mastered"' in client.get("/").text


def test_script_and_javascript_links_never_survive_rendering() -> None:
    html = str(
        render_markdown(
            "<script>alert(1)</script> <img src=x onerror=alert(1)> [x](javascript:alert(1))"
        )
    )
    assert "<script" not in html and "<img" not in html and "<a " not in html


def test_secrets_and_local_data_are_ignored_and_untracked() -> None:
    paths = [
        ".env",
        ".env.local",
        "data/hintkata.db",
        "workspace/x/solution.py",
        "a.db",
        "a.db-wal",
        ".cache/docs/x.md",
    ]
    git = ["git", "-C", str(ROOT)]
    ignored = subprocess.run([*git, "check-ignore", *paths], capture_output=True, text=True).stdout
    assert set(ignored.split()) == set(paths)
    tracked = subprocess.run(
        [*git, "ls-files", ".env", "data", "workspace", ".cache"], capture_output=True, text=True
    )
    assert tracked.stdout == ""
