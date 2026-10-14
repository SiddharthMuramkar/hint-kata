"""Task: read a streamed run two ways, as text deltas and as events."""

from pydantic_ai import Agent, FunctionToolCallEvent  # noqa: F401  (you will use these)


async def collect_deltas(agent: Agent[None, str], prompt: str) -> list[str]:
    """Run `agent` on `prompt` and return the streamed text as a list of deltas."""
    deltas: list[str] = []
    # TODO 1: open a streamed run with `agent.run_stream(prompt)` (an async context manager).
    #   - Loop over `result.stream_text(...)` and append each item to `deltas`.
    #   - You want only the NEW text of each chunk, not the text so far.
    #   - Give one list item per chunk: by default the chunks that arrive close together are
    #     grouped into one item. `stream_text` has an option that turns the grouping off.
    return deltas


async def tool_names(agent: Agent[None, str], prompt: str) -> list[str]:
    """Run `agent` on `prompt` and return the name of every tool the agent called, in order."""
    names: list[str] = []
    # TODO 2: open the run with `agent.run_stream_events(prompt)` (also an async context manager).
    #   - Loop over the events. Do not use a bare `async for` on the call itself.
    #   - When the agent is about to run a tool, the event is a `FunctionToolCallEvent`.
    #     Append the tool name from `event.part` to `names`.
    return names
