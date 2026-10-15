"""The runtime claims lesson PA11 makes about Pydantic AI 2.56.0, run for real.

No network, no Logfire account: a FunctionModel makes the loops, and an in-memory OpenTelemetry
exporter stands in for Logfire (Logfire's `instrument_pydantic_ai` switches on the same spans).
If a Pydantic AI upgrade changes one of these behaviours, the lesson text needs a second look.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic_ai import (
    Agent,
    ModelRetry,
    ToolFailed,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
    UsageLimits,
)
from pydantic_ai.capabilities import Instrumentation
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.instrumented import InstrumentationSettings


def looping_agent(
    tool: Callable[[str], str], calls_per_turn: int = 1, **kwargs: Any
) -> tuple[Agent[None, str], list[str]]:
    """An agent whose fake model calls `tool` on every turn, forever. `seen` records each call."""
    seen: list[str] = []
    reply = ModelResponse(parts=[ToolCallPart("work", {"q": "x"})] * calls_per_turn)
    agent = Agent(FunctionModel(lambda messages, info: reply), **kwargs)

    @agent.tool_plain
    def work(q: str) -> str:
        seen.append(q)
        return tool(q)

    return agent, seen


def raise_it(exc: Exception) -> Callable[[str], str]:
    def tool(q: str) -> str:
        raise exc

    return tool


def test_the_default_request_limit_is_50() -> None:
    agent, seen = looping_agent(lambda q: "ok")
    with pytest.raises(UsageLimitExceeded, match="request_limit of 50"):
        agent.run_sync("go")
    assert len(seen) == 50


def test_request_limit_stops_a_loop_after_that_many_turns() -> None:
    agent, seen = looping_agent(lambda q: "ok")
    with pytest.raises(UsageLimitExceeded, match="would exceed the request_limit of 3"):
        agent.run_sync("go", usage_limits=UsageLimits(request_limit=3))
    assert len(seen) == 3


def test_tool_calls_limit_is_checked_before_a_batch_runs() -> None:
    agent, seen = looping_agent(lambda q: "ok", calls_per_turn=3)
    with pytest.raises(UsageLimitExceeded, match="tool_calls_limit of 2"):
        agent.run_sync("go", usage_limits=UsageLimits(tool_calls_limit=2))
    assert seen == [], "three calls would pass the limit of 2, so none of them ran"


def test_a_tool_that_keeps_asking_for_a_retry_is_stopped_by_its_budget() -> None:
    agent, seen = looping_agent(raise_it(ModelRetry("again")))
    with pytest.raises(UnexpectedModelBehavior, match="max retries count of 1"):
        agent.run_sync("go")
    assert len(seen) == 2, "the default budget is one retry: two attempts"
    agent, seen = looping_agent(raise_it(ModelRetry("again")), retries={"tools": 3})
    with pytest.raises(UnexpectedModelBehavior, match="max retries count of 3"):
        agent.run_sync("go")
    assert len(seen) == 4


def test_a_tool_that_alternates_failure_and_success_never_uses_up_its_budget() -> None:
    calls: list[int] = []

    def flaky(q: str) -> str:
        calls.append(1)
        if len(calls) % 2:
            raise ModelRetry("odd call")
        return "ok"

    agent, _ = looping_agent(flaky)
    with pytest.raises(UsageLimitExceeded):  # only the request limit ends it
        agent.run_sync("go", usage_limits=UsageLimits(request_limit=10))
    assert len(calls) == 10


def test_tool_failed_does_not_use_the_retry_budget_or_the_tool_call_count() -> None:
    agent, seen = looping_agent(raise_it(ToolFailed("down")))
    limits = UsageLimits(request_limit=5, tool_calls_limit=2)
    with pytest.raises(UsageLimitExceeded, match="request_limit of 5"):
        agent.run_sync("go", usage_limits=limits)
    assert len(seen) == 5


def test_cost_limit_does_not_fire_for_a_model_with_no_price() -> None:
    agent, _ = looping_agent(lambda q: "ok")
    limits = UsageLimits(cost_limit=Decimal("0.0001"), request_limit=4)
    with pytest.raises(UsageLimitExceeded, match="request_limit of 4"):
        agent.run_sync("go", usage_limits=limits)


def test_a_stopped_run_leaves_one_agent_span_with_an_error_and_a_span_per_step() -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    settings = InstrumentationSettings(tracer_provider=provider, include_content=False)
    agent, _ = looping_agent(
        lambda q: "ok", name="looper", capabilities=[Instrumentation(settings=settings)]
    )
    with pytest.raises(UsageLimitExceeded):
        agent.run_sync("my-private-prompt", usage_limits=UsageLimits(request_limit=2))
    spans = exporter.get_finished_spans()
    assert [s.name.split(" ")[0] for s in spans] == [
        "chat",
        "execute_tool",
        "chat",
        "execute_tool",
        "invoke_agent",
    ]
    run_span = spans[-1]
    assert run_span.name == "invoke_agent looper" and run_span.status.status_code.name == "ERROR"
    assert all(s.parent is not None for s in spans[:-1]), "the steps hang under the run span"
    blob = " ".join(str(v) for s in spans for v in (s.attributes or {}).values())
    assert "my-private-prompt" not in blob, "include_content=False keeps prompts out"
    assert not any("tool.call.arguments" in k for s in spans for k in (s.attributes or {}))
