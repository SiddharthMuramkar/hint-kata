# ruff: noqa: E501
"""Record a scripted Pydantic AI run (FunctionModel, no network) as a trace.json.

uv run python traces/scripts/agent_run.py --out content/pydantic-ai/<lesson>/trace.json
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pydantic_ai  # noqa: E402
from pydantic_ai import Agent, ModelRetry, RunContext, models  # noqa: E402
from pydantic_ai.messages import (  # noqa: E402
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: E402

from app.traces import Annotation, Checkpoint, Citation, Step, Trace  # noqa: E402

models.ALLOW_MODEL_REQUESTS = False  # the script never talks to a real model

AGENT_DOC = Citation(url="https://pydantic.dev/docs/ai/core-concepts/agent/", title="Agents")
TEST_DOC = Citation(
    url="https://pydantic.dev/docs/ai/guides/testing/", title="Testing with FunctionModel"
)
PROMPT = "Do I need an umbrella in SF today?"
INSTRUCTIONS = "You are a weather assistant. Use get_forecast; never guess the weather."


@dataclass
class Deps:
    forecasts: dict[str, str]


def scripted_model(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Plays the LLM: decide by looking at the last part sent to the model."""
    last = messages[-1].parts[-1]
    if isinstance(last, UserPromptPart):
        return ModelResponse(parts=[ToolCallPart("get_forecast", {"city": "SF"})])
    if isinstance(last, RetryPromptPart):
        return ModelResponse(parts=[ToolCallPart("get_forecast", {"city": "San Francisco"})])
    assert isinstance(last, ToolReturnPart)
    return ModelResponse(
        parts=[TextPart(f"{last.content} Yes, bring an umbrella to San Francisco today.")]
    )


agent = Agent(
    FunctionModel(scripted_model),
    deps_type=Deps,
    instructions=INSTRUCTIONS,
    # No `name`: a FunctionModel agent would otherwise print a random name.
)


@agent.tool
def get_forecast(ctx: RunContext[Deps], city: str) -> str:
    """Return the forecast for a city (full name only)."""
    if city not in ctx.deps.forecasts:
        raise ModelRetry("City not found, try the full name")
    return ctx.deps.forecasts[city]


def clip(text: str, n: int = 300) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def build_steps(messages: list[ModelMessage]) -> list[Step]:
    steps: list[Step] = []

    def add(kind: str, actor: str, title: str, summary: str, payload: str = "", **extra) -> None:
        steps.append(
            Step(
                idx=len(steps),
                kind=kind,
                actor=actor,
                title=title,
                summary=summary,
                payload_excerpt=clip(payload),
                **extra,
            )
        )

    requests = 0
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, UserPromptPart):
                    add(
                        "user_prompt",
                        "user",
                        "The learner's question",
                        "The prompt starts a run.",
                        str(part.content),
                    )
                    if msg.instructions:
                        add(
                            "instructions",
                            "developer",
                            "Instructions travel with the prompt",
                            "Instructions are sent on every request but are not saved in history.",
                            msg.instructions,
                        )
                elif isinstance(part, RetryPromptPart):
                    add(
                        "retry",
                        "tool",
                        "The tool asked the model to try again",
                        "get_forecast raised ModelRetry; the message goes back to the model.",
                        part.model_response(),
                    )
                elif isinstance(part, ToolReturnPart):
                    add(
                        "tool_result",
                        "tool",
                        "The tool answered",
                        f"{part.tool_name} returned a value.",
                        str(part.content),
                    )
            requests += 1
            add(
                "model_request",
                "agent",
                f"Request {requests} to the model",
                "The agent sends the message history and the tool list to the model.",
            )
        elif isinstance(msg, ModelResponse):
            tokens = {
                "input_tokens": msg.usage.input_tokens,
                "output_tokens": msg.usage.output_tokens,
            }
            for part in msg.parts:
                if isinstance(part, ToolCallPart):
                    add(
                        "tool_call",
                        "model",
                        f"The model calls {part.tool_name}",
                        "The model returns a tool call instead of text.",
                        json.dumps(part.args_as_dict()),
                        metrics=tokens,
                    )
                elif isinstance(part, TextPart):
                    add(
                        "final_output",
                        "model",
                        "The model answers",
                        "Plain text ends the run.",
                        part.content,
                        metrics=tokens,
                    )
    return steps


def annotate(steps: list[Step]) -> None:
    """Author notes: why each step happened, plus two predict-next checkpoints."""
    notes = {
        "user_prompt": (
            "Every run starts from one prompt. Run state lives in the message history.",
            ["agent.run", "message history"],
            [AGENT_DOC],
        ),
        "instructions": (
            "`instructions=` is re-sent each request, so it always reflects the agent's current code.",
            ["instructions"],
            [AGENT_DOC],
        ),
        "model_request": (
            "One graph node per model call. A run is a loop of request, then tool calls, then request.",
            ["agent.iter", "nodes"],
            [AGENT_DOC],
        ),
        "tool_call": (
            "The model cannot run code. It names a tool and arguments; the agent runs it.",
            ["tools", "RunContext"],
            [AGENT_DOC],
        ),
        "retry": (
            "Raising ModelRetry turns a tool failure into feedback the model can act on; no crash.",
            ["ModelRetry", "tools"],
            [AGENT_DOC],
        ),
        "tool_result": (
            "The tool return value is added to history as a ToolReturnPart.",
            ["tools", "RunContext"],
            [AGENT_DOC],
        ),
        "final_output": (
            "A text answer with no tool call ends the run. FunctionModel scripted all of this, so no API key was needed.",
            ["FunctionModel", "testing"],
            [TEST_DOC],
        ),
    }
    for s in steps:
        why, tags, cites = notes[s.kind]
        s.annotation = Annotation(why=why, concept_tags=tags, citations=cites)
    first_request = next(s for s in steps if s.kind == "model_request")
    first_call = next(s for s in steps if s.kind == "tool_call")
    first_request.checkpoint = Checkpoint(
        type="predict_next",
        prompt="The model has the question and one tool, get_forecast. What does the agent do next?",
        options=["Answer directly", "Call get_forecast", "Ask the user a question"],
        answer=1,
        explanation="The instructions say never to guess, so the model returns a get_forecast tool call.",
    )
    first_call.checkpoint = Checkpoint(
        type="predict_next",
        prompt="The model called get_forecast with city='SF', which the tool rejects with ModelRetry. What happens?",
        options=[
            "The run crashes",
            "The error goes to the user",
            "The message goes back to the model for another try",
        ],
        answer=2,
        explanation="ModelRetry becomes a retry prompt in the history, and the model gets another request.",
    )


async def record() -> Trace:
    deps = Deps(forecasts={"San Francisco": "Rain, 14 C."})
    nodes: list[str] = []
    async with agent.iter(PROMPT, deps=deps) as run:
        async for node in run:
            nodes.append(type(node).__name__)
    assert run.result is not None
    steps = build_steps(run.result.all_messages())
    annotate(steps)
    usage = run.result.usage
    steps[-1].metrics |= {"total_tokens": usage.total_tokens, "requests": usage.requests}
    return Trace(
        id="pydantic-ai-agent-run",
        kind="pydantic_ai_run",
        title="Inside an agent run: a tool call, a retry and an answer",
        objectives=[
            "Follow the message flow of one Pydantic AI run, node by node.",
            "Explain what ModelRetry does when a tool rejects its arguments.",
        ],
        source={
            "generator": "FunctionModel",
            "script": "traces/scripts/agent_run.py",
            "pydantic_ai_version": pydantic_ai.__version__,
            "nodes": nodes,
            "captured_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        },
        steps=steps,
        takeaways=[
            "A run is a loop: model request, tool calls, model request, until the model returns text.",
            "ModelRetry feeds a tool error back to the model instead of failing the run.",
            "FunctionModel lets you script the model, so tests and traces need no API key.",
        ],
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    trace = asyncio.run(record())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(trace.model_dump_json(indent=2) + "\n")
    print(f"wrote {args.out} ({len(trace.steps)} steps)")


if __name__ == "__main__":
    main()
