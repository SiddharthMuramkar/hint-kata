# ruff: noqa: E501
"""Record a scripted, streamed Pydantic AI run (FunctionModel, no network) as a trace.json.

uv run python traces/scripts/agent_stream.py --out content/pydantic-ai/pa4-streaming/trace.json
"""

import argparse
import asyncio
import json
import sys
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pydantic_ai  # noqa: E402
from pydantic_ai import (  # noqa: E402
    Agent,
    AgentRunResultEvent,
    AgentStreamEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartEndEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
    ToolCallPart,
    ToolCallPartDelta,
    models,
)
from pydantic_ai.messages import ModelMessage, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import (  # noqa: E402
    AgentInfo,
    DeltaToolCall,
    DeltaToolCalls,
    FunctionModel,
)

from app.traces import Annotation, Checkpoint, Citation, Step, StepKind, Trace  # noqa: E402

models.ALLOW_MODEL_REQUESTS = False  # the script never talks to a real model

EVENTS_DOC = Citation(
    url="https://pydantic.dev/docs/ai/core-concepts/agent/#streaming-all-events",
    title="Agents: streaming all events",
)
STREAMED_DOC = Citation(
    url="https://pydantic.dev/docs/ai/core-concepts/output/#streamed-results",
    title="Output: streamed results",
)
PROMPT = "Do I need an umbrella in San Francisco today?"
# The scripted model sends the tool call in two pieces and the answer in four.
TOOL_CALL_PIECES = ['{"city": "San Fran', 'cisco"}']
TEXT_PIECES = ["Yes, ", "bring an umbrella: ", "rain is forecast ", "in San Francisco today."]

Record = tuple[AgentStreamEvent | AgentRunResultEvent, int]  # event, output tokens so far


async def scripted_stream(
    messages: list[ModelMessage], info: AgentInfo
) -> AsyncIterator[str | DeltaToolCalls]:
    """Plays the LLM as a stream: first a tool call in pieces, then the text in pieces."""
    if not any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
        first, rest = TOOL_CALL_PIECES
        yield {0: DeltaToolCall(name="get_forecast", json_args=first, tool_call_id="call_1")}
        yield {0: DeltaToolCall(json_args=rest)}
        return
    for piece in TEXT_PIECES:
        yield piece


agent = Agent(
    FunctionModel(stream_function=scripted_stream),
    # No `name`: a FunctionModel agent would otherwise print a random name.
)


@agent.tool_plain
def get_forecast(city: str) -> str:
    """Return the forecast for a city (full name only)."""
    return "Rain, 14 C."


def clip(text: str, n: int = 300) -> str:
    return text if len(text) <= n else text[: n - 1] + "…"


def build_steps(records: list[Record]) -> list[Step]:
    """Turn the event stream into steps. Part events are the model writing; FunctionTool events
    are the agent running a tool."""
    steps: list[Step] = []
    pieces: list[str] = []
    requests = 0
    in_request = False

    def add(
        kind: StepKind,
        actor: str,
        title: str,
        summary: str,
        why: str,
        tags: list[str],
        cite: Citation,
        payload: str = "",
        **extra,
    ) -> None:
        steps.append(
            Step(
                idx=len(steps),
                kind=kind,
                actor=actor,
                title=title,
                summary=summary,
                payload_excerpt=clip(payload),
                annotation=Annotation(why=why, concept_tags=tags, citations=[cite]),
                **extra,
            )
        )

    add(
        "user_prompt",
        "user",
        "The learner's question",
        "The prompt starts a run.",
        "A streamed run starts like any other run: one prompt, then a loop of model requests.",
        ["run_stream_events"],
        EVENTS_DOC,
        PROMPT,
    )
    for event, tokens_so_far in records:
        if isinstance(event, PartStartEvent):
            if not in_request:
                requests += 1
                in_request = True
                add(
                    "model_request",
                    "agent",
                    f"Request {requests} to the model",
                    "The agent sends the message history and the tool list. The reply comes back as events.",
                    "With a streamed run the reply is not one object. It is a stream of events, one part at a time.",
                    ["streaming", "events"],
                    EVENTS_DOC,
                )
            pieces.clear()
            if isinstance(event.part, TextPart):
                add(
                    "model_text",
                    "model",
                    "PartStartEvent: a text part opens",
                    "The first piece of text arrives inside the start event.",
                    "PartStartEvent carries the first piece of a new part. Later pieces arrive as PartDeltaEvent.",
                    ["PartStartEvent", "text"],
                    EVENTS_DOC,
                    event.part.content,
                )
            elif isinstance(event.part, ToolCallPart):
                pieces.append(str(event.part.args))
        elif isinstance(event, PartDeltaEvent):
            if isinstance(event.delta, ToolCallPartDelta):
                pieces.append(str(event.delta.args_delta))
            elif isinstance(event.delta, TextPartDelta):
                pieces.append(event.delta.content_delta)
        elif isinstance(event, PartEndEvent):
            if isinstance(event.part, ToolCallPart):
                add(
                    "tool_call",
                    "model",
                    f"The model streams a call to {event.part.tool_name}",
                    "A PartStartEvent opened a tool-call part. A PartDeltaEvent carried the rest of the arguments.",
                    "This is the model writing, not your code running. The arguments are only usable once the part ends.",
                    ["PartStartEvent", "PartDeltaEvent"],
                    EVENTS_DOC,
                    " | ".join(repr(p) for p in pieces),
                )
            elif isinstance(event.part, TextPart):
                add(
                    "model_text",
                    "model",
                    "PartDeltaEvent: the rest of the text arrives in pieces",
                    "Each piece is a PartDeltaEvent. A PartEndEvent closes the part.",
                    "A delta holds only the new piece, never the text so far. Add the pieces up yourself, or let stream_text do it.",
                    ["PartDeltaEvent", "delta"],
                    EVENTS_DOC,
                    " | ".join(repr(p) for p in pieces),
                    metrics={"usage_output_tokens_so_far": tokens_so_far},
                )
        elif isinstance(event, FinalResultEvent):
            add(
                "model_text",
                "agent",
                "FinalResultEvent: this reply is the answer",
                "The agent has seen enough to know this response is the final result.",
                "run_stream stops at the first output that matches the output type. This event marks that point.",
                ["FinalResultEvent", "run_stream"],
                STREAMED_DOC,
                f"tool_name={event.tool_name}",
            )
        elif isinstance(event, FunctionToolCallEvent):
            add(
                "tool_call",
                "agent",
                f"FunctionToolCallEvent: the agent runs {event.part.tool_name}",
                "The model's call is complete. Now the agent calls your function.",
                "The Part events described the model writing the call. This event is your function about to run.",
                ["FunctionToolCallEvent", "tools"],
                EVENTS_DOC,
                json.dumps(event.part.args_as_dict()),
            )
        elif isinstance(event, FunctionToolResultEvent):
            in_request = False
            add(
                "tool_result",
                "tool",
                "FunctionToolResultEvent: the tool answered",
                f"{event.part.tool_name} returned a value. The agent will send it to the model.",
                "The result goes into the history and the next model request streams a new reply.",
                ["FunctionToolResultEvent", "tools"],
                EVENTS_DOC,
                str(event.part.content),
            )
        elif isinstance(event, AgentRunResultEvent):
            usage = event.result.usage
            add(
                "final_output",
                "agent",
                "AgentRunResultEvent: the run is finished",
                "The last event carries the finished run, with its output and total usage.",
                "Read usage here or after the stream ends. Earlier totals are partial. FunctionModel estimates tokens, so no API key was needed.",
                ["AgentRunResultEvent", "usage"],
                EVENTS_DOC,
                str(event.result.output),
                metrics={
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "total_tokens": usage.total_tokens,
                    "requests": usage.requests,
                    "tool_calls": usage.tool_calls,
                },
            )
    return steps


def add_checkpoints(steps: list[Step]) -> None:
    """Two predict-next checkpoints."""
    first_request = next(s for s in steps if s.kind == "model_request")
    last_text = [s for s in steps if s.kind == "model_text"][-1]
    first_request.checkpoint = Checkpoint(
        type="predict_next",
        prompt="The model's reply to request 1 is a tool call, and it is streaming in. Which event do you see first?",
        options=["FunctionToolCallEvent", "PartStartEvent", "AgentRunResultEvent"],
        answer=1,
        explanation="The reply arrives as parts. A PartStartEvent opens the tool-call part. FunctionToolCallEvent comes later, when the agent is about to run your function.",
    )
    last_text.checkpoint = Checkpoint(
        type="predict_next",
        prompt="All the text has arrived. If you read the run's usage right now, do you have the final total?",
        options=[
            "Yes, the answer is complete so the total is complete",
            "No, trust the total only when the run is finished",
            "No, usage is only counted for tool calls",
        ],
        answer=1,
        explanation="The run is not finished until AgentRunResultEvent. A total read mid-stream is partial, so read usage at the end.",
    )


async def record() -> Trace:
    records: list[Record] = []
    async with agent.run_stream_events(PROMPT) as events:
        async for event in events:
            records.append((event, events.usage.output_tokens))
    steps = build_steps(records)
    add_checkpoints(steps)
    return Trace(
        id="pydantic-ai-stream-events",
        kind="pydantic_ai_run",
        title="Inside a streamed run: a tool call in pieces, then the answer in pieces",
        objectives=[
            "Tell apart the events for what the model writes and the events for what the agent runs.",
            "Say when the usage of a streamed run is complete.",
        ],
        source={
            "generator": "FunctionModel",
            "script": "traces/scripts/agent_stream.py",
            "pydantic_ai_version": pydantic_ai.__version__,
            "events": [type(event).__name__ for event, _ in records],
            "captured_at": datetime.now(UTC).strftime("%Y-%m-%d"),
        },
        steps=steps,
        takeaways=[
            "run_stream_events is an async context manager. It yields every event of the whole run and ends with AgentRunResultEvent.",
            "Part events show what the model is writing. FunctionTool events show what the agent runs.",
            "Read usage when the run is finished. A total read mid-stream is partial.",
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
