from typing import Any

import pytest
from desk import DeskDeps, desk_agent, stock_agent
from pydantic_ai import UsageLimits, models
from pydantic_ai.exceptions import UsageLimitExceeded, UserError
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False  # no test here may reach a real model

QUESTION = "Do you still have tea in stock?"


def _parts(messages: list[ModelMessage]) -> list[Any]:
    return [part for message in messages for part in message.parts]


def _run(stock: dict[str, int], **kwargs: Any) -> tuple[Any, DeskDeps, list[str], list[list[str]]]:
    """Run the desk agent with a scripted fake model on BOTH agents.

    Returns the result, the deps, a log of which agent was asked, and the user prompts the stock
    agent's model received.
    """
    deps = DeskDeps(stock=stock)
    log: list[str] = []
    stock_prompts: list[list[str]] = []

    def desk(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        log.append("desk")
        returns = [p for p in _parts(messages) if isinstance(p, ToolReturnPart)]
        if not returns:
            return ModelResponse(parts=[ToolCallPart("check_stock", {"item": "tea"})])
        return ModelResponse(parts=[TextPart(f"We have {returns[-1].content} in stock.")])

    def warehouse(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        log.append("stock")
        stock_prompts.append(
            [str(p.content) for p in _parts(messages) if isinstance(p, UserPromptPart)]
        )
        returns = [p for p in _parts(messages) if isinstance(p, ToolReturnPart)]
        if not returns:
            return ModelResponse(parts=[ToolCallPart("count_in_warehouse", {"item": "tea"})])
        return ModelResponse(
            parts=[ToolCallPart("final_result", {"response": returns[-1].content})]
        )

    try:
        with (
            desk_agent.override(model=FunctionModel(desk)),
            stock_agent.override(model=FunctionModel(warehouse)),
        ):
            result = desk_agent.run_sync(QUESTION, deps=deps, **kwargs)
    except UserError as error:
        pytest.fail(f"the tool must be `async def` and use `await ...run(...)`: {error}")
    return result, deps, log, stock_prompts


def test_the_answer_comes_from_the_stock_agent() -> None:
    result, _, log, _ = _run({"tea": 12})
    assert result.output == "We have 12 in stock."
    assert log == ["desk", "stock", "stock", "desk"], "the desk must wait for the stock agent"


def test_the_stock_agent_gets_the_item_in_its_prompt() -> None:
    _, _, _, prompts = _run({"tea": 12})
    assert any("tea" in prompt for prompt in prompts[0]), "the prompt must name the item"


def test_the_stock_agent_uses_the_same_deps_object() -> None:
    result, deps, _, _ = _run({"tea": 3})
    assert result.output == "We have 3 in stock."  # not a number from somewhere else
    assert deps.asked == ["tea"], "pass `deps=ctx.deps` so the delegate works on your deps"


def test_the_usage_of_both_agents_is_counted() -> None:
    result, _, _, _ = _run({"tea": 12})
    assert result.usage.requests == 4, "2 desk requests + 2 stock requests; pass `usage=ctx.usage`"
    assert result.usage.tool_calls == 2


def test_a_request_limit_on_the_desk_run_covers_the_stock_agent() -> None:
    with pytest.raises(UsageLimitExceeded):
        _run({"tea": 12}, usage_limits=UsageLimits(request_limit=3))


def test_the_stock_agent_does_not_see_the_customers_conversation() -> None:
    _, _, _, prompts = _run({"tea": 12})
    assert all(QUESTION not in prompt for prompt in prompts[0]), (
        "do not pass `message_history`: the delegate starts clean"
    )
