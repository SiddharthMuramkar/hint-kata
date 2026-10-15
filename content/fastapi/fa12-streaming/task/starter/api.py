from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

app = FastAPI()


class Step(BaseModel):
    n: int
    text: str


STEPS = [
    Step(n=1, text="read"),
    Step(n=2, text="quiz"),
    Step(n=3, text="think\ndeeper"),
]


# TODO 1 (JSON Lines): this route builds the whole list and returns it, so the client gets one
#   JSON array with the content type `application/json`. Make it a stream: use `yield` to send
#   one `Step` at a time, and declare the return type `AsyncIterable[Step]`. FastAPI then writes
#   one JSON object per line, with the content type `application/jsonl`.
@app.get("/steps/lines")
async def lines() -> list[Step]:
    return STEPS


# TODO 2 (named events): this is an SSE route, but every event is a plain `data:` block with no
#   name, and the last one is the JSON string "done" (with quotes). Fix it so that:
#   - each step is sent as an event named `step`, with the `id` set to the step number as text
#     (`id="1"`, `id="2"`, ...), and the step itself in `data`;
#   - after the steps comes one event named `done`, whose `data:` line is exactly `[DONE]`,
#     with no quotes. Think about which field of `ServerSentEvent` does not encode its value.
@app.get("/steps/events", response_class=EventSourceResponse)
async def events() -> AsyncIterable[ServerSentEvent]:
    for step in STEPS:
        yield ServerSentEvent(data=step)
    yield ServerSentEvent(data="done")
