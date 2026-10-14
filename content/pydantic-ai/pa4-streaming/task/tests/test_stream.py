import asyncio
from collections.abc import AsyncIterator

from pydantic_ai import Agent, models
from pydantic_ai.messages import ModelMessage, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, DeltaToolCalls, FunctionModel
from stream import collect_deltas, tool_names

models.ALLOW_MODEL_REQUESTS = False  # no test here may reach a real model

CHUNKS = ["Tea ", "costs ", "2.75 ", "with tax."]


async def text_script(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
    """A fake model that streams a plain text answer in four chunks."""
    for chunk in CHUNKS:
        yield chunk


async def tool_script(
    messages: list[ModelMessage], info: AgentInfo
) -> AsyncIterator[str | DeltaToolCalls]:
    """A fake model: call price_of (arguments in two pieces), then add_tax, then stream text."""
    returned = sum(isinstance(p, ToolReturnPart) for m in messages for p in m.parts)
    if returned == 0:
        yield {0: DeltaToolCall(name="price_of", json_args='{"item": "te', tool_call_id="c1")}
        yield {0: DeltaToolCall(json_args='a"}')}
    elif returned == 1:
        yield {0: DeltaToolCall(name="add_tax", json_args='{"price": 2.5}', tool_call_id="c2")}
    else:
        for chunk in CHUNKS:
            yield chunk


def text_agent() -> Agent[None, str]:
    return Agent(FunctionModel(stream_function=text_script))


def tool_agent() -> Agent[None, str]:
    agent = Agent(FunctionModel(stream_function=tool_script))

    @agent.tool_plain
    def price_of(item: str) -> float:
        """Price of an item."""
        return 2.5

    @agent.tool_plain
    def add_tax(price: float) -> float:
        """Add tax to a price."""
        return 2.75

    return agent


def test_collect_deltas_returns_one_item_per_chunk() -> None:
    got = asyncio.run(collect_deltas(text_agent(), "How much is tea?"))
    assert got == CHUNKS, (
        "expected the four chunks the model sent, as four list items. "
        "Ask for deltas (not the text so far) and turn off the grouping of chunks."
    )


def test_collect_deltas_skips_the_tool_calls() -> None:
    got = asyncio.run(collect_deltas(tool_agent(), "How much is tea?"))
    assert got == CHUNKS, "the deltas should be only the text of the final answer"


def test_tool_names_are_in_the_order_they_were_called() -> None:
    got = asyncio.run(tool_names(tool_agent(), "How much is tea?"))
    assert got == ["price_of", "add_tax"]


def test_tool_names_is_empty_when_no_tool_is_called() -> None:
    assert asyncio.run(tool_names(text_agent(), "Hello")) == []
