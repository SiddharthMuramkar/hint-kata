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

from app.agents.tutor import STATIC_INSTRUCTIONS, TutorDeps, lesson_context, make_tutor
from app.routes.tutor import get_tutor
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
    return TutorDeps(title, ceiling, 1, **fields)


def lesson(title: str = "Demo") -> str:
    return lesson_context([("intro", "Intro", f"Body of {title}.")])


async def wire(*turns: tuple[str, TutorDeps]) -> list[dict[str, Any]]:
    """Stream one reply per (lesson text, deps) from the real tutor agent for that lesson, as the
    route does, and return every request body it sent."""
    bodies: list[dict[str, Any]] = []

    def answer(request: httpx2.Request) -> httpx2.Response:
        bodies.append(json.loads(request.content))
        return httpx2.Response(200, headers={"content-type": "text/event-stream"}, content=STREAM)

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(answer)) as client:
        model = OpenRouterModel(
            "anthropic/claude-haiku-5.5",
            provider=OpenRouterProvider(api_key="fake", http_client=client),
        )
        # Only for this block: the transport is the mock above, so no request leaves the machine.
        with override_allow_model_requests(True):
            for text, d in turns:
                tutor = make_tutor(model, text)
                async with tutor.run_stream("hi", deps=d) as result:
                    await result.get_output()
    return bodies


def static_text(body: dict[str, Any]) -> str:
    (block,) = body["messages"][0]["content"]  # a list of one block: the marker needs a block
    return str(block["text"])


@pytest.mark.anyio
async def test_the_cached_block_holds_the_rules_and_the_lesson_sections() -> None:
    (body,) = await wire((lesson(), deps()))
    assert body["stream"] is True  # the route streams, so this is the request it really makes
    messages = body["messages"]
    assert [m["role"] for m in messages] == ["system", "system", "user"]
    static, dynamic, user = messages
    assert isinstance(static["content"], list), "no marker: the instructions were all dynamic"
    (block,) = static["content"]
    assert block["text"].startswith(STATIC_INSTRUCTIONS)
    assert "[§intro] Intro\nBody of Demo." in block["text"]  # the sections are cached too
    assert block["cache_control"] == {"type": "ephemeral", "ttl": "5m"}
    assert isinstance(dynamic["content"], str)  # the per-turn part stays a plain string
    assert "Demo" in dynamic["content"] and "L2" in dynamic["content"]
    assert "Body of Demo" not in dynamic["content"]  # the sections left the per-turn part
    assert json.dumps(body).count("cache_control") == 1  # one marker, covering rules and sections
    assert "cache_control" not in json.dumps([dynamic, user])


@pytest.mark.anyio
async def test_a_turn_changes_only_the_per_turn_part_but_another_lesson_changes_the_block() -> None:
    a1, a2, b, edited = await wire(
        (lesson("Demo"), deps("Demo", 1)),
        (lesson("Demo"), deps("Demo", 5, escalate=True)),
        (lesson("Another lesson"), deps("Another lesson", 1)),
        (lesson("Demo") + " (edited)", deps("Demo", 1)),
    )
    assert a1["messages"][0] == a2["messages"][0]  # same lesson: the cache hits
    assert a1["messages"][1] != a2["messages"][1]
    assert static_text(a1) != static_text(b)  # another lesson: a different block
    assert static_text(a1) != static_text(edited)  # an edited lesson: a new block, no stale hit
    assert static_text(b).startswith(STATIC_INSTRUCTIONS)


@pytest.mark.anyio
async def test_per_turn_facts_are_in_the_dynamic_part_only() -> None:
    (body,) = await wire(
        (lesson(), deps("Demo", 3, misconceptions=["mixes up Depends and Body"], escalate=True))
    )
    dynamic = body["messages"][1]["content"]
    for fact in ("'Demo'", "L3", "1 attempt", "mixes up Depends", "stuck"):
        assert fact in dynamic
    assert "Demo" not in STATIC_INSTRUCTIONS and "mixes up" not in static_text(body)


def test_one_agent_per_lesson_text_is_reused() -> None:
    get_tutor.cache_clear()
    assert get_tutor(lesson()) is get_tutor(lesson())
    assert get_tutor(lesson()) is not get_tutor(lesson("Another lesson"))
    get_tutor.cache_clear()


def test_the_static_part_is_long_enough_to_cache_and_holds_the_fixed_rules() -> None:
    assert len(STATIC_INSTRUCTIONS) // 4 >= 512  # Anthropic caches nothing shorter on Haiku 5.5
    for rung in LADDER:
        assert rung in STATIC_INSTRUCTIONS
    text = STATIC_INSTRUCTIONS.casefold()
    for rule in ("[§section-id]", "[src:N]", "when retrieved documentation is present"):
        assert rule.casefold() in text  # the [src:N] rule is always there, only for docs turns
    assert "<<<USER>>>" in STATIC_INSTRUCTIONS and "<<<DOCS>>>" in STATIC_INSTRUCTIONS
