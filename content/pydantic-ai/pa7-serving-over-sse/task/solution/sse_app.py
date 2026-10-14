"""Task: serve an agent over Server-Sent Events from a POST endpoint."""

from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.models import Model


def make_agent(model: Model) -> Agent[None, str]:
    """Already written. The tests pass in a model with a scripted reply, so no API key is needed."""
    return Agent(model, instructions="Answer in one short sentence.")


class ChatIn(BaseModel):
    message: str


def make_app(agent: Agent[None, str]) -> FastAPI:
    app = FastAPI()

    @app.post("/chat", response_class=EventSourceResponse)
    async def chat(body: ChatIn) -> AsyncIterable[ServerSentEvent]:
        parts: list[str] = []
        async with agent.run_stream(body.message) as result:
            # delta=True: only the new text. debounce_by=None: one item per chunk.
            async for delta in result.stream_text(delta=True, debounce_by=None):
                parts.append(delta)
                yield ServerSentEvent(event="token", data=delta)
        yield ServerSentEvent(event="done", data="".join(parts))

    return app
