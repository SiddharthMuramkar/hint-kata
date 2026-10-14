"""Hidden checks for PA5. They use TestModel and FunctionModel, so no API key or network is needed."""

import importlib
import json
from pathlib import Path
from types import ModuleType

import pytest
from pydantic_ai import models
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

models.ALLOW_MODEL_REQUESTS = False  # a real model call would be a bug

# History written to disk by the reference solution after one turn.
STORED_JSON = (
    '[{"parts":[{"content":"My name is Ana.","timestamp":"2026-10-14T14:47:55.124307Z",'
    '"part_kind":"user-prompt"}],"timestamp":"2026-10-14T14:47:55.124520Z",'
    '"instructions":"You are a friendly chat partner. Be concise.","kind":"request",'
    '"run_id":"01a13ae2-59e1-77cd-99d6-970f04eb97b2",'
    '"conversation_id":"01a13ae2-59e1-77cd-99d6-971022a161c7","metadata":null,'
    '"state":"complete"},{"parts":[{"content":"Nice to meet you, Ana.","id":null,'
    '"provider_name":null,"provider_details":null,"part_kind":"text"}],'
    '"usage":{"input_tokens":55,"cache_write_tokens":0,"cache_read_tokens":0,'
    '"output_tokens":6,"input_audio_tokens":0,"cache_audio_read_tokens":0,'
    '"output_audio_tokens":0,"audio_seconds":0.0,"details":{},"cost":null},'
    '"model_name":"test","timestamp":"2026-10-14T14:47:55.124784Z","kind":"response",'
    '"provider_name":"test","provider_url":null,"provider_details":null,'
    '"provider_response_id":null,"finish_reason":null,'
    '"run_id":"01a13ae2-59e1-77cd-99d6-970f04eb97b2",'
    '"conversation_id":"01a13ae2-59e1-77cd-99d6-971022a161c7","metadata":null,'
    '"workspace_ref":null,"failed_attempts":null,"state":"complete"}]'
)


@pytest.fixture
def chat_mod(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    # `test` is the built-in fake model, so make_agent() works without an API key.
    monkeypatch.setenv("TUTOR_MODEL", "test")
    return importlib.import_module("chat")


def user_texts(messages: list[ModelMessage]) -> list[str]:
    return [
        str(part.content)
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, UserPromptPart)
    ]


def recording_model(seen: list[list[ModelMessage]]) -> FunctionModel:
    """A fake model that records the messages it receives and answers 'reply N'."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(list(messages))
        return ModelResponse(parts=[TextPart(f"reply {len(seen)}")])

    return FunctionModel(respond)


def test_ask_returns_the_reply_text(chat_mod: ModuleType) -> None:
    chat = chat_mod.Chat()
    with chat.agent.override(model=TestModel(custom_output_text="Hello Ana")):
        assert chat.ask("Hi, I am Ana.") == "Hello Ana"


def test_second_ask_sees_the_first_turn(chat_mod: ModuleType) -> None:
    seen: list[list[ModelMessage]] = []
    chat = chat_mod.Chat()
    with chat.agent.override(model=recording_model(seen)):
        chat.ask("My name is Ana.")
        chat.ask("What is my name?")
    assert len(seen) == 2
    assert user_texts(seen[0]) == ["My name is Ana."]
    # The second run got the first request and reply as history, plus the new question.
    assert len(seen[1]) == 3
    assert user_texts(seen[1]) == ["My name is Ana.", "What is my name?"]
    assert isinstance(seen[1][1], ModelResponse)


def test_history_grows_by_one_turn_and_is_not_duplicated(chat_mod: ModuleType) -> None:
    seen: list[list[ModelMessage]] = []
    chat = chat_mod.Chat()
    with chat.agent.override(model=recording_model(seen)):
        for text in ("one", "two", "three"):
            chat.ask(text)
    assert len(chat.messages) == 6, "each turn adds one request and one reply, nothing more"
    assert user_texts(chat.messages) == ["one", "two", "three"]
    assert [len(m) for m in seen] == [1, 3, 5]


def test_save_writes_a_json_list_of_messages(chat_mod: ModuleType, tmp_path: Path) -> None:
    chat = chat_mod.Chat()
    with chat.agent.override(model=TestModel(custom_output_text="ok")):
        chat.ask("one")
        chat.ask("two")
    path = tmp_path / "chat.json"
    chat.save(path)
    data = json.loads(path.read_text())
    assert [m["kind"] for m in data] == ["request", "response", "request", "response"]


def test_save_then_load_round_trips_and_the_chat_continues(
    chat_mod: ModuleType, tmp_path: Path
) -> None:
    first = chat_mod.Chat()
    with first.agent.override(model=TestModel(custom_output_text="Nice to meet you.")):
        first.ask("My name is Ana.")
    path = tmp_path / "chat.json"
    first.save(path)

    seen: list[list[ModelMessage]] = []
    second = chat_mod.Chat()
    second.load(path)
    assert second.messages == first.messages
    assert isinstance(second.messages[0], ModelRequest)
    assert isinstance(second.messages[1], ModelResponse)
    with second.agent.override(model=recording_model(seen)):
        second.ask("What is my name?")
    assert user_texts(seen[0]) == ["My name is Ana.", "What is my name?"]


def test_loads_json_written_by_the_reference_solution(
    chat_mod: ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "stored.json"
    path.write_text(STORED_JSON)
    seen: list[list[ModelMessage]] = []
    chat = chat_mod.Chat()
    chat.load(path)
    assert user_texts(chat.messages) == ["My name is Ana."]
    with chat.agent.override(model=recording_model(seen)):
        chat.ask("What is my name?")
    assert user_texts(seen[0]) == ["My name is Ana.", "What is my name?"]
    assert len(chat.messages) == 4


def test_load_replaces_the_history_instead_of_adding_to_it(
    chat_mod: ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "stored.json"
    path.write_text(STORED_JSON)
    chat = chat_mod.Chat()
    with chat.agent.override(model=TestModel(custom_output_text="ok")):
        chat.ask("something else")
    chat.load(path)
    assert user_texts(chat.messages) == ["My name is Ana."]
    assert len(chat.messages) == 2
