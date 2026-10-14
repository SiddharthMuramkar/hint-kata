from collections.abc import Callable
from typing import Any

from pydantic_ai import models
from pydantic_ai.messages import (
    ModelMessage,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from tools_task import Deps, make_agent  # ty: ignore[unresolved-import]

models.ALLOW_MODEL_REQUESTS = False  # no test here may reach a real model

PRICES = {"tea": 2.5, "coffee": 3.0}


def _parts(messages: list[ModelMessage]) -> list[Any]:
    return [part for message in messages for part in message.parts]


def scripted(seen_retry: list[str]) -> Callable[[list[ModelMessage], AgentInfo], ModelResponse]:
    """A fake model: asks for a bad item, reads the retry hint, asks for a good one, answers."""

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        parts = _parts(messages)
        returns = [p for p in parts if isinstance(p, ToolReturnPart)]
        retries = [p for p in parts if isinstance(p, RetryPromptPart)]
        if returns:
            return ModelResponse(parts=[TextPart(f"Tea costs {returns[-1].content}.")])
        if retries:
            seen_retry.append(retries[-1].model_response())
            return ModelResponse(parts=[ToolCallPart("price_of", {"item": "tea"})])
        return ModelResponse(parts=[ToolCallPart("price_of", {"item": "teaa"})])

    return model


def test_agent_declares_deps_and_registers_the_tool() -> None:
    agent = make_agent()
    assert agent.deps_type is Deps
    advertised: list[str] = []

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        advertised.extend(t.name for t in info.function_tools)
        return ModelResponse(parts=[TextPart("ok")])

    agent.run_sync("hi", model=FunctionModel(model), deps=Deps(prices=PRICES))
    assert advertised == ["price_of"]


def test_unknown_item_sends_a_retry_prompt_and_the_model_recovers() -> None:
    seen_retry: list[str] = []
    result = make_agent().run_sync(
        "How much is tea?",
        model=FunctionModel(scripted(seen_retry)),
        deps=Deps(prices=PRICES),
    )
    assert len(seen_retry) == 1, "the bad item should produce exactly one retry prompt"
    assert "Unknown item, try one of:" in seen_retry[0]
    assert "coffee" in seen_retry[0] and "tea" in seen_retry[0]
    assert "2.5" in result.output


def test_tool_reads_prices_from_deps_not_from_a_global() -> None:
    seen_retry: list[str] = []
    result = make_agent().run_sync(
        "How much is tea?",
        model=FunctionModel(scripted(seen_retry)),
        deps=Deps(prices={"tea": 9.75}),
    )
    assert "9.75" in result.output
    assert "coffee" not in seen_retry[0]
