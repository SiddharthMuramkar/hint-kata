"""Tests for support_agent. They use TestModel and FunctionModel, so no real model is called."""

import pytest
from pydantic_ai import capture_run_messages, models
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from support_agent import SupportDeps, SupportReply, support_agent

models.ALLOW_MODEL_REQUESTS = False  # no test in this file may reach a real model

TOOLS = {"lookup_order", "refund"}


def call(name: str, **args: object) -> ModelResponse:
    """A scripted model reply that calls one tool."""
    return ModelResponse(parts=[ToolCallPart(name, args)])


def answer(order_id: str, refunded: bool, message: str) -> ModelResponse:
    """A scripted model reply that gives the final, structured answer."""
    return call("final_result", order_id=order_id, refunded=refunded, message=message)


def scripted(*replies: ModelResponse) -> FunctionModel:
    """A fake model that returns the given replies one by one."""
    remaining = iter(replies)

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return next(remaining)

    return FunctionModel(respond)


def tool_calls(messages: list[ModelMessage]) -> list[tuple[str, dict]]:
    """The (name, arguments) of every tool the model asked for, in order. Skips the answer."""
    return [
        (part.tool_name, part.args_as_dict())
        for message in messages
        if isinstance(message, ModelResponse)
        for part in message.parts
        if isinstance(part, ToolCallPart) and part.tool_name in TOOLS
    ]


def retry_prompts(messages: list[ModelMessage]) -> list[RetryPromptPart]:
    return [
        part
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, RetryPromptPart)
    ]


HAPPY_PATH = (
    call("lookup_order", order_id="A1"),
    call("refund", order_id="A1", amount=20.0),
    answer("A1", True, "Refunded 20.0"),
)


def test_testmodel_looks_up_the_order_before_it_refunds() -> None:
    deps = SupportDeps(orders={"a": 10.0})  # TestModel invents the id "a"
    with capture_run_messages() as messages:
        with support_agent.override(model=TestModel()):
            result = support_agent.run_sync("Refund my order", deps=deps)
    assert tool_calls(messages) == [
        ("lookup_order", {"order_id": "a"}),
        ("refund", {"order_id": "a", "amount": 0.0}),
    ]
    assert result.output == SupportReply(order_id="a", refunded=False, message="a")
    assert deps.refunds == ["a"]


def test_scripted_happy_path() -> None:
    deps = SupportDeps(orders={"A1": 20.0})
    with capture_run_messages() as messages:
        with support_agent.override(model=scripted(*HAPPY_PATH)):
            result = support_agent.run_sync("Refund order A1", deps=deps)
    assert tool_calls(messages) == [
        ("lookup_order", {"order_id": "A1"}),
        ("refund", {"order_id": "A1", "amount": 20.0}),
    ]
    assert result.output == SupportReply(order_id="A1", refunded=True, message="Refunded 20.0")
    assert deps.refunds == ["A1"]
    assert retry_prompts(messages) == []


def test_refund_before_lookup_is_rejected_and_the_model_recovers() -> None:
    deps = SupportDeps(orders={"A1": 20.0})
    model = scripted(call("refund", order_id="A1", amount=20.0), *HAPPY_PATH)
    with capture_run_messages() as messages:
        with support_agent.override(model=model):
            support_agent.run_sync("Refund order A1", deps=deps)
    (retry,) = retry_prompts(messages)
    assert retry.tool_name == "refund"
    assert "Look up order 'A1'" in retry.content
    assert deps.refunds == ["A1"]  # refunded once, and only after the lookup


def test_unknown_order_sends_a_retry_prompt() -> None:
    deps = SupportDeps(orders={"A1": 20.0})
    model = scripted(call("lookup_order", order_id="ZZ"), *HAPPY_PATH)
    with capture_run_messages() as messages:
        with support_agent.override(model=model):
            support_agent.run_sync("Refund order ZZ", deps=deps)
    (retry,) = retry_prompts(messages)
    assert retry.tool_name == "lookup_order"
    assert retry.content == "Unknown order 'ZZ'. Known orders: A1"


def test_refunding_more_than_was_paid_is_rejected() -> None:
    deps = SupportDeps(orders={"A1": 20.0})
    model = scripted(
        call("lookup_order", order_id="A1"),
        call("refund", order_id="A1", amount=99.0),
        call("refund", order_id="A1", amount=20.0),
        answer("A1", True, "Refunded 20.0"),
    )
    with capture_run_messages() as messages:
        with support_agent.override(model=model):
            support_agent.run_sync("Refund order A1", deps=deps)
    (retry,) = retry_prompts(messages)
    assert retry.content == "You can refund at most 20.0."
    assert deps.refunds == ["A1"]


def test_the_run_fails_when_the_model_keeps_asking_for_an_unknown_order() -> None:
    deps = SupportDeps(orders={"A1": 20.0})
    bad = call("lookup_order", order_id="ZZ")
    with pytest.raises(UnexpectedModelBehavior, match="lookup_order"):
        with support_agent.override(model=scripted(bad, bad)):
            support_agent.run_sync("Refund order ZZ", deps=deps)
    assert deps.refunds == []


def test_the_fake_model_sees_both_tools_and_a_structured_answer() -> None:
    seen: list[tuple[list[str], list[str]]] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(([t.name for t in info.function_tools], [t.name for t in info.output_tools]))
        return answer("A1", False, "Nothing to do")

    with support_agent.override(model=FunctionModel(respond)):
        support_agent.run_sync("Hello", deps=SupportDeps(orders={}))
    assert seen == [(["lookup_order", "refund"], ["final_result"])]


def test_usage_counts_requests_and_tool_calls() -> None:
    with support_agent.override(model=scripted(*HAPPY_PATH)):
        result = support_agent.run_sync("Refund order A1", deps=SupportDeps(orders={"A1": 20.0}))
    assert result.usage.requests == 3  # lookup, refund, answer
    assert result.usage.tool_calls == 2


def test_a_run_without_an_override_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")  # so the model object can be built
    with pytest.raises(RuntimeError, match="not allowed"):
        support_agent.run_sync("Hello", deps=SupportDeps(orders={}))
