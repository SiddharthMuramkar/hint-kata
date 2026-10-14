"""Task: read a streamed run two ways, as text deltas and as events."""

from pydantic_ai import Agent, FunctionToolCallEvent


async def collect_deltas(agent: Agent[None, str], prompt: str) -> list[str]:
    """Run `agent` on `prompt` and return the streamed text as a list of deltas."""
    deltas: list[str] = []
    async with agent.run_stream(prompt) as result:
        # delta=True: only the new text of each chunk. debounce_by=None: one item per chunk.
        async for delta in result.stream_text(delta=True, debounce_by=None):
            deltas.append(delta)
    return deltas


async def tool_names(agent: Agent[None, str], prompt: str) -> list[str]:
    """Run `agent` on `prompt` and return the name of every tool the agent called, in order."""
    names: list[str] = []
    async with agent.run_stream_events(prompt) as events:
        async for event in events:
            if isinstance(event, FunctionToolCallEvent):
                names.append(event.part.tool_name)
    return names
