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


# `yield` makes the route a stream. With `AsyncIterable[Step]`, FastAPI writes one JSON object per
# line and sets the content type to `application/jsonl`.
@app.get("/steps/lines")
async def lines() -> AsyncIterable[Step]:
    for step in STEPS:
        yield step


# `event` names the event, `id` must be text, and `raw_data` is sent without JSON encoding.
@app.get("/steps/events", response_class=EventSourceResponse)
async def events() -> AsyncIterable[ServerSentEvent]:
    for step in STEPS:
        yield ServerSentEvent(data=step, event="step", id=str(step.n))
    yield ServerSentEvent(raw_data="[DONE]", event="done")
