"""Hidden checks for PA3. A scripted FunctionModel plays the model, so no API key is needed."""

import importlib
from typing import Any

import pytest
from pydantic import ValidationError
from pydantic_ai import Agent, models
from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False  # no test here may reach a real model

GOOD = {"category": "bug", "priority": 2, "summary": "Invoice PDF will not open"}


@pytest.fixture
def triage(monkeypatch: pytest.MonkeyPatch):
    # `test` is the built-in fake model, so make_agent() works without an API key.
    monkeypatch.setenv("TUTOR_MODEL", "test")
    return importlib.import_module("triage")


def scripted(*answers: dict[str, Any]) -> FunctionModel:
    """A fake model that answers with each dict in turn, through the output tool."""
    calls = iter(answers)

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        tool = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(tool, next(calls))])

    return FunctionModel(model)


def retry_prompts(result: Any) -> list[RetryPromptPart]:
    return [
        part
        for message in result.all_messages()
        for part in message.parts
        if isinstance(part, RetryPromptPart)
    ]


def test_ticket_fields_are_plain(triage) -> None:
    fields = triage.Ticket.model_fields
    assert set(fields) == {"category", "priority", "summary"}
    assert fields["priority"].annotation is int
    assert fields["summary"].annotation is str
    assert triage.Ticket(**GOOD).priority == 2
    with pytest.raises(ValidationError):
        triage.Ticket(**{**GOOD, "category": "banana"})
    # The rules live in the output validator, so the model class itself accepts these values.
    triage.Ticket(category="bug", priority=9, summary="x" * 200)


def test_make_agent_returns_agent_with_ticket_output(triage) -> None:
    agent = triage.make_agent()
    assert isinstance(agent, Agent)
    assert agent.output_type is triage.Ticket


def test_valid_ticket_needs_no_retry(triage) -> None:
    result = triage.make_agent().run_sync("hi", model=scripted(GOOD))
    assert isinstance(result.output, triage.Ticket)
    assert retry_prompts(result) == []
    assert result.usage.requests == 1


def test_boundaries_are_accepted(triage) -> None:
    edge = {"category": "billing", "priority": 5, "summary": "x" * 120}
    result = triage.make_agent().run_sync("hi", model=scripted(edge))
    assert retry_prompts(result) == []
    assert result.output.priority == 5
    low = triage.make_agent().run_sync("hi", model=scripted({**edge, "priority": 1}))
    assert retry_prompts(low) == []


@pytest.mark.parametrize("bad_priority", [0, 6, 9, -1])
def test_priority_out_of_range_triggers_a_retry(triage, bad_priority: int) -> None:
    result = triage.make_agent().run_sync(
        "hi", model=scripted({**GOOD, "priority": bad_priority}, GOOD)
    )
    prompts = retry_prompts(result)
    assert len(prompts) == 1, "the validator should send exactly one retry prompt"
    # A string means ModelRetry sent it. Pydantic's own failures carry a list of errors.
    assert isinstance(prompts[0].content, str), "raise ModelRetry from the validator"
    text = prompts[0].content.lower()
    assert "priority" in text and "1" in text and "5" in text
    assert isinstance(result.output, triage.Ticket)
    assert result.output.priority == 2
    assert result.usage.requests == 2


def test_long_summary_triggers_a_retry(triage) -> None:
    too_long = {**GOOD, "summary": "x" * 121}
    result = triage.make_agent().run_sync("hi", model=scripted(too_long, GOOD))
    prompts = retry_prompts(result)
    assert len(prompts) == 1, "the validator should send exactly one retry prompt"
    assert isinstance(prompts[0].content, str), "raise ModelRetry from the validator"
    assert "120" in prompts[0].content
    assert len(result.output.summary) <= 120
    assert result.output.summary == GOOD["summary"]


def test_retry_prompt_reaches_the_model(triage) -> None:
    # The second request to the model must carry the retry prompt.
    seen: list[list[ModelMessage]] = []
    calls = iter([{**GOOD, "priority": 7}, GOOD])

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(list(messages))
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, next(calls))])

    triage.make_agent().run_sync("hi", model=FunctionModel(model))
    assert len(seen) == 2
    assert any(isinstance(part, RetryPromptPart) for m in seen[1] for part in m.parts), (
        "the retry prompt should be part of the second request"
    )
