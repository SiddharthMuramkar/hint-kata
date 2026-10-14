import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from app.config import settings
from app.main import app
from app.routes.tutor import get_tutor
from app.store import open_store
from app.tutor_rules import (
    LADDER,
    apply_ceiling,
    compute_ceiling,
    defuse,
    no_progress,
    number_sources,
    validate_citations,
    validate_sources,
)

models.ALLOW_MODEL_REQUESTS = False
FIXTURES = Path(__file__).parent / "fixtures" / "content"
REPLY = "See [§intro] and [§nope]. ```python\nx=1\n```"


def test_ladder_has_seven_rungs() -> None:
    assert [r[:2] for r in LADDER] == [f"L{i}" for i in range(7)]


@pytest.mark.parametrize(
    ("attempts", "quiz", "revealed", "expected"),
    [
        (0, False, False, 1),
        (2, False, False, 3),
        (9, False, False, 6),
        (5, True, False, 2),
        (0, True, False, 1),
        (0, False, True, 6),
    ],
)
def test_compute_ceiling(attempts: int, quiz: bool, revealed: bool, expected: int) -> None:
    assert compute_ceiling(attempts, quiz, revealed) == expected


def test_apply_ceiling_strips_fences_below_l4_only() -> None:
    text = "a\n```py\nx=1\n```\nb\n~~~\ny=2\n~~~\n"
    low = apply_ceiling(text, 3)
    assert "```" not in low and "~~~" not in low and "x=1" not in low
    assert "[code withheld at hint level L3 — attempt the task first]" in low
    assert apply_ceiling(text, 4) == text


def test_validate_citations_drops_unknown_and_keeps_order() -> None:
    text, ids = validate_citations("[§b] x [§zzz] [§a] [§b]", {"a", "b"})
    assert ids == ["b", "a"]
    assert "zzz" not in text and "[§a]" in text


@pytest.mark.parametrize(
    ("text", "n", "kept", "ids"),
    [
        ("a [src:1] b [src:2]", 2, "a [src:1] b [src:2]", [1, 2]),
        ("a [src:9] b [src:1]", 2, "a  b [src:1]", [1]),  # out of range: dropped
        ("[src:2] [src:1] [src:2]", 3, "[src:2] [src:1] [src:2]", [2, 1]),  # first-use order
        ("[src:0] [src:-1] [src:01] [src:1.0]", 5, "   ", []),  # only 1..n exactly
        ("[src:1,2] [src:x] [src:] [src: 1]", 5, "   ", []),  # not a single number
        ("see [src:1] and [§a]", 0, "see  and [§a]", []),  # no docs this turn: all dropped
        ("[src:1\n2] [src:99999999999999999999]", 3, "[src:1\n2] ", []),  # no newline; huge number
    ],
)
def test_validate_sources_keeps_only_numbers_given_this_turn(
    text: str, n: int, kept: str, ids: list[int]
) -> None:
    assert validate_sources(text, n) == (kept, ids)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a <<< b <<<< c", "a << b << c"),
        ("\uff1c\uff1c\uff1cEND\uff1e\uff1e\uff1e", "<<END>>>"),  # fullwidth look-alikes
        ("<\u200b<\u200b<USER", "<<USER"),  # zero-width characters between the brackets
        ("<\u00ad<\ufeff<", "<<"),  # soft hyphen and byte order mark
        ("plain <b>text</b> and << two", "plain <b>text</b> and << two"),
    ],
)
def test_defuse_leaves_no_triple_bracket_delimiter(text: str, expected: str) -> None:
    assert defuse(text) == expected
    assert "<<<" not in defuse(text)


def test_number_sources_keeps_the_number_without_a_hole() -> None:
    assert number_sources("a [src:1] b [src:12] [§x]") == "a [1] b [12] [§x]"


def test_no_progress() -> None:
    same = [{"role": "user", "content": "I'm stuck"}, {"role": "assistant", "content": "?"}]
    assert no_progress([*same, {"role": "user", "content": "  I'M STUCK "}])
    assert not no_progress([*same, {"role": "user", "content": "now try Depends"}])
    assert not no_progress(same)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "content_root", str(FIXTURES))
    monkeypatch.setattr(settings, "hintkata_db_path", str(tmp_path / "t.db"))
    with TestClient(app) as c, get_tutor().override(model=TestModel(custom_output_text=REPLY)):
        yield c


def _events(body: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in lines:
            out[lines["event"]] = json.loads(lines["data"])
    return out


def _chat(client: TestClient, message: str = "help", item: str | None = None) -> dict[str, Any]:
    r = client.post("/api/tutor/fx-demo", json={"message": message, "active_item": item})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "event: html" in r.text and "event: citations" in r.text
    return _events(r.text)


def test_chat_streams_enforces_ceiling_and_persists(client: TestClient) -> None:
    ev = _chat(client)
    assert "```" not in str(ev["html"]) and "<pre" not in str(ev["html"])
    assert "nope" not in str(ev["html"])
    assert [c["id"] for c in ev["citations"]] == ["intro"]
    assert ev["citations"][0]["href"] == "#intro"
    turns = client.get("/api/tutor/fx-demo/history").json()
    assert [t["role"] for t in turns] == ["user", "assistant"]
    assert turns[0]["text"] == "help"
    assert turns[1]["ceiling"] == "L1" and "nope" not in turns[1]["html"]


def test_reveal_logs_event_and_lifts_ceiling(client: TestClient) -> None:
    r = client.post("/api/tutor/fx-demo/reveal", json={"item_id": "q1"})
    assert r.json()["answer"] == "A function"
    assert client.post("/api/tutor/fx-demo/reveal", json={"item_id": "d1"}).json()["answer"] == (
        "Reuse and testability."
    )
    assert client.post("/api/tutor/fx-demo/reveal", json={"item_id": "q3"}).json()["answer"] == (
        "Depends"
    )
    assert client.post("/api/tutor/fx-demo/reveal", json={"item_id": "zz"}).status_code == 404
    ev = _chat(client)
    assert "x=1" in str(ev["html"])  # ceiling 6 keeps the code
    assert client.get("/api/tutor/fx-demo/history").json()[1]["ceiling"] == "L6"


def _due_keys(hours: int) -> dict[str, str]:
    store = open_store(settings.hintkata_db_path)
    try:
        later = (datetime.now(UTC) + timedelta(hours=hours)).isoformat()
        return {c["item_key"]: c["due"] for c in store.due_cards(store.ensure_user("owner"), later)}
    finally:
        store.close()


def test_reveal_quiz_item_schedules_retest_within_a_day(client: TestClient) -> None:
    body = client.post("/api/tutor/fx-demo/reveal", json={"item_id": "q1"}).json()
    due = _due_keys(25)["fx-demo:q1"]
    assert datetime.fromisoformat(due) <= datetime.now(UTC) + timedelta(hours=24)
    assert body["next_due"] == due


def test_reveal_deeper_question_schedules_one_card_per_criterion(client: TestClient) -> None:
    body = client.post("/api/tutor/fx-demo/reveal", json={"item_id": "d1"}).json()
    dues = [due for k, due in _due_keys(25).items() if k.startswith("fx-demo:d1#")]
    assert len(dues) == 3
    assert body["next_due"] == min(dues)


def test_revealing_twice_keeps_one_card(client: TestClient) -> None:
    for _ in range(2):
        client.post("/api/tutor/fx-demo/reveal", json={"item_id": "q1"})
    assert [k for k in _due_keys(25) if k == "fx-demo:q1"] == ["fx-demo:q1"]


def test_unknown_lesson_is_404(client: TestClient) -> None:
    assert client.post("/api/tutor/nope", json={"message": "x"}).status_code == 404
    assert client.get("/api/tutor/nope/history").status_code == 404


def test_active_item_caps_ceiling_even_after_reveal(client: TestClient) -> None:
    client.post("/api/tutor/fx-demo/reveal", json={"item_id": "q1"})
    ev = _chat(client, item="q1")
    assert "x=1" not in str(ev["html"]) and "<pre" not in str(ev["html"])
    assert ev["ceiling"] == "L2"
    assert client.get("/api/tutor/fx-demo/history").json()[1]["ceiling"] == "L2"


def test_no_tokens_below_l4_and_tokens_at_l4(client: TestClient) -> None:
    low = client.post("/api/tutor/fx-demo", json={"message": "a"}).text
    assert "event: token" not in low and "x=1" not in low.split("event: html")[0]
    client.post("/api/tutor/fx-demo/reveal", json={"item_id": "q1"})
    assert "event: token" in client.post("/api/tutor/fx-demo", json={"message": "b"}).text


def test_script_and_javascript_links_do_not_survive(client: TestClient) -> None:
    evil = "<script>alert(1)</script> [x](javascript:alert(1))"
    with get_tutor().override(model=TestModel(custom_output_text=evil)):
        html = str(_chat(client)["html"])
    assert "<script" not in html and "<a " not in html  # escaped text, no live link
