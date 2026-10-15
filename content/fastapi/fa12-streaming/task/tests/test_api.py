import json

import api  # the learner's api.py, on PYTHONPATH
from fastapi.testclient import TestClient

client = TestClient(api.app)


def parse_sse(text: str) -> list[dict[str, str]]:
    """Cut an SSE body into events. Blocks end at a blank line, comment lines are skipped."""
    events = []
    for block in text.split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            if line and not line.startswith(":"):
                key, _, value = line.partition(": ")
                fields[key] = value
        if fields:
            events.append(fields)
    return events


def test_steps_are_unchanged():
    assert [s.n for s in api.STEPS] == [1, 2, 3], "leave STEPS as it is"


def test_lines_is_jsonl():
    response = client.get("/steps/lines")
    content_type = response.headers["content-type"]
    assert content_type.startswith("application/jsonl"), (
        f"content type is {content_type!r}: the route must yield, one Step at a time"
    )


def test_lines_has_one_object_per_line():
    lines = client.get("/steps/lines").text.splitlines()
    assert len(lines) == 3, f"expected 3 lines, got {len(lines)}"
    assert [json.loads(line) for line in lines] == [s.model_dump() for s in api.STEPS]


def test_events_is_event_stream():
    response = client.get("/steps/events")
    assert response.headers["content-type"].startswith("text/event-stream")


def test_events_are_named_in_order():
    names = [e.get("event") for e in parse_sse(client.get("/steps/events").text)]
    assert names == ["step", "step", "step", "done"], f"event names were {names}"


def test_step_events_carry_id_and_data():
    events = parse_sse(client.get("/steps/events").text)[:3]
    assert [e.get("id") for e in events] == ["1", "2", "3"], "id must be the step number as text"
    assert [json.loads(e["data"]) for e in events] == [s.model_dump() for s in api.STEPS]


def test_done_event_is_raw():
    last = parse_sse(client.get("/steps/events").text)[-1]
    assert last.get("data") == "[DONE]", (
        f"the data line was {last.get('data')!r}: it must be exactly [DONE], with no quotes"
    )
