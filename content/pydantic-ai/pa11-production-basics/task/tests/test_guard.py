import ast
from collections.abc import Iterator
from pathlib import Path

import guard
from guard import Deps, Outcome, run_guarded
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False  # no test here may reach a real model


def call(name: str, **args: object) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart(name, args)])


def answer(text: str) -> ModelResponse:
    return ModelResponse(parts=[TextPart(text)])


def forever(reply: ModelResponse) -> FunctionModel:
    """A fake model that gives the same reply on every turn: a runaway loop."""
    return FunctionModel(lambda messages, info: reply)


def scripted(*replies: ModelResponse) -> FunctionModel:
    remaining: Iterator[ModelResponse] = iter(replies)

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return next(remaining)

    return FunctionModel(respond)


def run(model: FunctionModel) -> tuple[Outcome, Deps]:
    deps = Deps()
    with guard.agent.override(model=model):
        return run_guarded("Question?", deps), deps


def test_a_run_that_finishes_gives_the_answer() -> None:
    outcome, deps = run(scripted(call("search", query="pydantic"), answer("Done.")))
    assert outcome == Outcome(finished=True, text="Done.", reason="")
    assert deps.searches == ["pydantic"]


def test_a_search_loop_is_stopped_after_three_tool_calls() -> None:
    outcome, deps = run(forever(call("search", query="again")))
    assert outcome.finished is False and outcome.text == ""
    assert len(deps.searches) == 3, "tool_calls_limit should allow exactly 3 successful calls"
    assert "tool_calls_limit" in outcome.reason


def test_a_loop_of_failing_tool_calls_is_stopped_by_the_request_limit() -> None:
    # ToolFailed is not a successful call and does not use the retry budget, so only
    # request_limit can stop this loop.
    outcome, deps = run(forever(call("fetch", url="https://down.example/page")))
    assert outcome.finished is False
    assert len(deps.fetches) == 5, "request_limit should allow exactly 5 model turns"
    assert "request_limit" in outcome.reason


def test_a_tool_can_ask_for_two_retries_and_the_run_still_finishes() -> None:
    model = scripted(
        call("fetch", url="ftp://bad"),
        call("fetch", url="http://also-bad"),
        call("fetch", url="https://good.example"),
        answer("Fetched."),
    )
    outcome, deps = run(model)
    assert outcome == Outcome(finished=True, text="Fetched.", reason="")
    assert len(deps.fetches) == 3, "the tool needs a retry budget of 2 to survive two bad calls"


def test_a_tool_that_keeps_asking_for_retries_is_stopped_by_its_budget() -> None:
    outcome, deps = run(forever(call("fetch", url="ftp://bad")))
    assert outcome.finished is False
    assert len(deps.fetches) == 3, "a budget of 2 retries means 3 attempts in all"
    assert "max retries count of 2" in outcome.reason


def test_the_run_text_is_empty_and_the_reason_is_set_when_stopped() -> None:
    outcome, _ = run(forever(call("search", query="again")))
    assert outcome.text == "" and outcome.reason != ""


def test_the_code_does_not_hide_the_limits_in_a_bare_except() -> None:
    tree = ast.parse(Path(guard.__file__).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            names = (
                {n.id for n in ast.walk(node.type) if isinstance(n, ast.Name)}
                if node.type
                else set()
            )
            assert names, "catch the two named exceptions, not everything"
            assert not names & {"Exception", "BaseException"}, (
                "do not catch Exception: a bug in your tool should still show up"
            )
