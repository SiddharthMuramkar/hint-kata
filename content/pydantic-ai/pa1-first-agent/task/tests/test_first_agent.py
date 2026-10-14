"""Hidden checks for PA1. They use TestModel, so no API key or network is needed."""

import importlib

import pytest
from pydantic_ai import Agent, models
from pydantic_ai.models.test import TestModel

models.ALLOW_MODEL_REQUESTS = False  # a real model call would be a bug


@pytest.fixture
def first_agent(monkeypatch: pytest.MonkeyPatch):
    # `test` is the built-in fake model, so make_agent() works without an API key.
    monkeypatch.setenv("TUTOR_MODEL", "test")
    return importlib.import_module("first_agent")


def test_city_facts_has_three_fields(first_agent) -> None:
    fields = first_agent.CityFacts.model_fields
    assert set(fields) == {"city", "country", "population"}
    assert fields["city"].annotation is str
    assert fields["country"].annotation is str
    assert fields["population"].annotation is int


def test_make_agent_returns_agent_with_output_type(first_agent) -> None:
    agent = first_agent.make_agent()
    assert isinstance(agent, Agent)
    assert agent.output_type is first_agent.CityFacts


def test_model_comes_from_tutor_model_env(first_agent) -> None:
    # TUTOR_MODEL=test was set by the fixture, so the agent must be using TestModel.
    assert isinstance(first_agent.make_agent().model, TestModel)


def test_run_returns_city_facts(first_agent) -> None:
    agent = first_agent.make_agent()
    with agent.override(model=TestModel()):
        result = agent.run_sync("Tell me about Lisbon.")
    assert isinstance(result.output, first_agent.CityFacts)


def test_instructions_mention_concise(first_agent) -> None:
    agent = first_agent.make_agent()
    with agent.override(model=TestModel()):
        result = agent.run_sync("Tell me about Lisbon.")
    sent = [getattr(m, "instructions", None) for m in result.all_messages()]
    instructions = next((i for i in sent if i), "")
    assert instructions, "Pass your text with `instructions=`, not `system_prompt=`."
    assert "concise" in instructions.lower()
