"""Task: serve an agent over Server-Sent Events from a POST endpoint."""

from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent  # noqa: F401  (you will use these)
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

    # TODO 1: make this route an SSE route. Add the argument that tells FastAPI to send
    #   `text/event-stream`. Without it, a generator endpoint streams JSON lines instead.
    @app.post("/chat")
    async def chat(body: ChatIn) -> AsyncIterable[ServerSentEvent]:
        parts: list[str] = []
        # TODO 2: run the agent on `body.message` as a stream: `async with agent.run_stream(...)`.
        #   - Loop over `result.stream_text(...)`. You want only the NEW text of each chunk, and
        #     one item per chunk (the tests use a fast, scripted model).
        #   - Keep each piece in `parts`, and `yield` it as a `ServerSentEvent` named "token".
        # TODO 3: after the loop, `yield` one `ServerSentEvent` named "done".
        #   Its data is the full text: all the pieces joined.
        yield ServerSentEvent(event="token", data="TODO " + "".join(parts))  # delete this line

    return app
