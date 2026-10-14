"""The tutor's cache marker, checked on the OpenRouter wire. The real OpenRouterModel runs behind a
mock transport: the request body is built exactly as in production, nothing leaves the machine and
no API key is needed."""

import json
from typing import Any

import httpx2
import pytest
from pydantic_ai.models import override_allow_model_requests
from pydantic_ai.models.openrouter import OpenRouterModel
from pydantic_ai.providers.openrouter import OpenRouterProvider

from app.agents.tutor import STATIC_INSTRUCTIONS, TutorDeps, make_tutor
from app.tutor_rules import LADDER


def sse(delta: dict[str, Any], finish: str | None = None) -> str:
    chunk = {
        "id": "gen-1",
        "object": "chat.completion.chunk",
        "created": 0,
        "model": "anthropic/claude-haiku-5.5",
        "provider": "Anthropic",
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }
    return f"data: {json.dumps(chunk)}\n\n"


STREAM = sse({"role": "assistant", "content": "ok"}) + sse({}, "stop") + "data: [DONE]\n\n"


def deps(title: str = "Demo", ceiling: int = 2, **more: Any) -> TutorDeps:
    fields: dict[str, Any] = {"misconceptions": [], "escalate": False} | more
    return TutorDeps(title, [("intro", "Intro", f"Body of {title}.")], ceiling, 1, **fields)


async def wire(*turns: TutorDeps) -> list[dict[str, Any]]:
    """Stream one reply per deps from the real tutor agent, as the route does, and return every
    request body it sent."""
    bodies: list[dict[str, Any]] = []

    def answer(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.content))
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=STREAM)

    model = OpenRouterModel(
        "anthropic/claude-haiku-5.5",
        provider=OpenRouterProvider(
            api_key="fake",
            http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(answer)),
        ),
    )
    tutor = make_tutor("openrouter:anthropic/claude-haiku-5.5")
    # Only for this block: the transport is the mock above, so no request can leave the machine.
    with override_allow_model_requests(True), tutor.override(model=model):
        for d in turns:
            async with tutor.run_stream("hi", deps=d) as result:
                await result.get_output()
    return bodies


@pytest.mark.anyio
async def test_only_the_static_instructions_carry_the_cache_marker() -> None:
    (body,) = await wire(deps())
    assert body["stream"] is True  # the route streams, so this is the request it really makes
    messages = body["messages"]
    assert [m["role"] for m in messages] == ["system", "system", "user"]
    static, dynamic, user = messages
    assert isinstance(static["content"], list), "no marker: the instructions were all dynamic"
    (block,) = static["content"]  # a list of one block: the marker needs a block to sit on
    assert block["text"] == STATIC_INSTRUCTIONS
    assert block["cache_control"]["type"] == "ephemeral"
    assert isinstance(dynamic["content"], str)  # the per-turn part stays a plain string
    assert "Demo" in dynamic["content"] and "L2" in dynamic["content"]
    assert json.dumps(body).count("cache_control") == 1  # not on the per-turn part or the user turn
    assert "cache_control" not in json.dumps([dynamic, user])


@pytest.mark.anyio
async def test_the_cached_bytes_never_change_between_turns_or_lessons() -> None:
    first, second = await wire(deps("Demo", 1), deps("Another lesson", 5, escalate=True))
    assert first["messages"][0] == second["messages"][0]
    assert first["messages"][1] != second["messages"][1]


@pytest.mark.anyio
async def test_per_turn_facts_are_in_the_dynamic_part_only() -> None:
    (body,) = await wire(
        deps("Demo", 3, misconceptions=["mixes up Depends and Body"], escalate=True)
    )
    static, dynamic = (m["content"] for m in body["messages"][:2])
    assert STATIC_INSTRUCTIONS == static[0]["text"]
    for fact in ("'Demo'", "[§intro]", "L3", "1 attempt", "mixes up Depends", "stuck"):
        assert fact in dynamic
    assert "Demo" not in STATIC_INSTRUCTIONS and "mixes up" not in STATIC_INSTRUCTIONS


def test_the_static_part_is_long_enough_to_cache_and_holds_the_fixed_rules() -> None:
    assert len(STATIC_INSTRUCTIONS) // 4 >= 512  # Anthropic caches nothing shorter on Haiku 5.5
    for rung in LADDER:
        assert rung in STATIC_INSTRUCTIONS
    text = STATIC_INSTRUCTIONS.casefold()
    for rule in ("[§section-id]", "[src:N]", "when retrieved documentation is present"):
        assert rule.casefold() in text  # the [src:N] rule is always there, only for docs turns
    assert "<<<USER>>>" in STATIC_INSTRUCTIONS and "<<<DOCS>>>" in STATIC_INSTRUCTIONS
