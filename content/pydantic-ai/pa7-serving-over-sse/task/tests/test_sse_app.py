import json
from collections.abc import AsyncIterator, Iterable
from typing import Any

from fastapi.testclient import TestClient
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sse_app import make_agent, make_app

models.ALLOW_MODEL_REQUESTS = False  # no test here may reach a real model

CHUNKS = ["Tea ", "costs ", "2.75 ", "with tax."]
PROMPTS: list[str] = []


async def script(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
    """A fake model that notes the prompt it got and streams its answer in four chunks."""
    for message in messages:
        for part in message.parts:
            if isinstance(part, UserPromptPart):
                PROMPTS.append(str(part.content))
    for chunk in CHUNKS:
        yield chunk


def parse_events(lines: Iterable[str]) -> list[tuple[str, Any]]:
    """Group SSE lines into blocks (a blank line ends one) and return (event name, data)."""
    events: list[tuple[str, Any]] = []
    name, data = "message", ""
    for line in lines:
        if line == "":
            if data:  # a block with no data line, such as ': ping', is not an event
                events.append((name, json.loads(data)))
            name, data = "message", ""
        elif line.startswith("event: "):
            name = line[len("event: ") :]
        elif line.startswith("data: "):
            data += line[len("data: ") :]
    return events


def post_chat() -> tuple[str, list[tuple[str, Any]]]:
    """POST /chat and return the Content-Type and the parsed events.

    TestClient runs the whole app before it hands anything back, so these tests check
    WHAT arrived, not WHEN. (To see the timing you need a real server and httpx.stream.)
    """
    client = TestClient(make_app(make_agent(FunctionModel(stream_function=script))))
    with client.stream("POST", "/chat", json={"message": "How much is tea?"}) as response:
        return response.headers["content-type"], parse_events(response.iter_lines())


def test_response_is_an_event_stream() -> None:
    content_type, _ = post_chat()
    assert content_type.startswith("text/event-stream"), (
        f"got Content-Type {content_type!r}. "
        "Pass response_class=EventSourceResponse to the route decorator."
    )


def test_text_arrives_as_token_events() -> None:
    _, events = post_chat()
    tokens = [data for name, data in events if name == "token"]
    assert len(tokens) >= 2, (
        f"expected at least 2 'token' events, got {len(tokens)}. A scripted model is fast, "
        "so ask stream_text for one item per chunk."
    )
    assert "".join(tokens) == "".join(CHUNKS), (
        "the token events should hold only the NEW text of each chunk, not the text so far"
    )


def test_done_event_carries_the_full_text() -> None:
    _, events = post_chat()
    names = [name for name, _ in events]
    assert names.count("done") == 1 and names[-1] == "done", (
        f"expected one 'done' event, last. Got the events: {names}"
    )
    assert events[-1][1] == "".join(CHUNKS), "the 'done' data should be the whole text"


def test_the_request_message_reaches_the_agent() -> None:
    PROMPTS.clear()
    post_chat()
    assert PROMPTS == ["How much is tea?"], "run the agent on body.message"
