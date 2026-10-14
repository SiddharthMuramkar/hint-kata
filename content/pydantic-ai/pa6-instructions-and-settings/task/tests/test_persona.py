"""Hidden checks for PA6. A recording FunctionModel plays the model, so no API key is needed."""

import dataclasses
import importlib
from types import ModuleType

import pytest
from pydantic_ai import Agent, models
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False  # no test here may reach a real model


@pytest.fixture
def persona() -> ModuleType:
    return importlib.import_module("persona")


def recording_model(seen: list[AgentInfo]) -> FunctionModel:
    """A fake model that keeps what each request carried: instructions and settings."""

    def model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(info)
        return ModelResponse(parts=[TextPart("ok")])

    return FunctionModel(model)


def test_deps_is_a_dataclass_with_tone_and_max_words(persona: ModuleType) -> None:
    assert dataclasses.is_dataclass(persona.PersonaDeps)
    assert [f.name for f in dataclasses.fields(persona.PersonaDeps)] == ["tone", "max_words"]
    deps = persona.PersonaDeps("brief", 40)
    assert (deps.tone, deps.max_words) == ("brief", 40)


def test_make_agent_builds_without_a_key(persona: ModuleType) -> None:
    assert isinstance(persona.make_agent(), Agent)


def test_instructions_carry_the_static_text_then_the_deps(persona: ModuleType) -> None:
    seen: list[AgentInfo] = []
    agent = persona.make_agent()
    with agent.override(model=recording_model(seen)):
        persona.ask(agent, "hi", persona.PersonaDeps("brief", 40))
    text = seen[0].instructions or ""
    assert text.startswith(persona.STATIC), "keep the static instructions first"
    dynamic = text.removeprefix(persona.STATIC)
    assert "brief" in dynamic, "the dynamic text should name the tone from deps"
    assert "40" in dynamic, "the dynamic text should give the word limit from deps"


def test_instructions_are_rebuilt_from_the_new_deps_on_every_run(persona: ModuleType) -> None:
    seen: list[AgentInfo] = []
    agent = persona.make_agent()
    with agent.override(model=recording_model(seen)):
        first = persona.ask(agent, "hi", persona.PersonaDeps("brief", 40))
        persona.ask(
            agent, "again", persona.PersonaDeps("formal", 120), history=first.all_messages()
        )
    assert len(seen) == 2
    second = seen[1].instructions or ""
    assert "formal" in second and "120" in second
    assert "brief" not in second and "40" not in second, "the model must not see the old deps"
    assert second.startswith(persona.STATIC)


def test_settings_for_scales_max_tokens_with_the_tone(persona: ModuleType) -> None:
    assert persona.settings_for("brief")["max_tokens"] == 150
    assert persona.settings_for("friendly")["max_tokens"] == 300
    assert persona.settings_for("formal")["max_tokens"] == 450
    assert persona.settings_for("sarcastic")["max_tokens"] == 300  # not in the table


@pytest.mark.parametrize("tone", ["brief", "friendly", "formal", "sarcastic"])
def test_settings_for_sets_only_max_tokens(persona: ModuleType, tone: str) -> None:
    # Claude 5.x models take no temperature or top_p. This site never sets them.
    assert set(persona.settings_for(tone)) == {"max_tokens"}


@pytest.mark.parametrize(
    ("tone", "expected"), [("brief", 150), ("friendly", 300), ("formal", 450), ("sarcastic", 300)]
)
def test_the_run_setting_beats_the_agent_setting_and_the_rest_merge(
    persona: ModuleType, tone: str, expected: int
) -> None:
    seen: list[AgentInfo] = []
    agent = persona.make_agent()
    with agent.override(model=recording_model(seen)):
        persona.ask(agent, "hi", persona.PersonaDeps(tone, 40))
    settings = seen[0].model_settings or {}
    assert settings["max_tokens"] == expected, "run-level max_tokens should win over the agent's"
    assert settings["timeout"] == 20, "settings the run does not name should stay"


def test_each_run_gets_the_cap_for_its_own_tone(persona: ModuleType) -> None:
    seen: list[AgentInfo] = []
    agent = persona.make_agent()
    with agent.override(model=recording_model(seen)):
        persona.ask(agent, "one", persona.PersonaDeps("brief", 40))
        persona.ask(agent, "two", persona.PersonaDeps("formal", 40))
        persona.ask(agent, "three", persona.PersonaDeps("brief", 40))
    caps = [(info.model_settings or {})["max_tokens"] for info in seen]
    assert caps == [150, 450, 150]


def test_ask_returns_the_run_result(persona: ModuleType) -> None:
    seen: list[AgentInfo] = []
    agent = persona.make_agent()
    with agent.override(model=recording_model(seen)):
        result = persona.ask(agent, "hi", persona.PersonaDeps("brief", 40))
    assert result.output == "ok"
