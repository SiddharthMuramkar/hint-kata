import html
import json
import logging
import re
from collections.abc import AsyncIterable
from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fsrs import Rating
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from app import retrieval
from app.agents.tutor import TutorDeps, format_sources, make_tutor
from app.config import settings
from app.content import Lesson, Source
from app.deps import get_store, get_user_id
from app.markdown import render_markdown
from app.review import criterion_item_id, record_result
from app.store import Store
from app.tutor_rules import (
    apply_ceiling,
    compute_ceiling,
    defuse,
    no_progress,
    number_sources,
    validate_citations,
    validate_sources,
)

router = APIRouter(prefix="/api/tutor")
log = logging.getLogger(__name__)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    active_item: str | None = None


class RevealIn(BaseModel):
    item_id: str


@lru_cache
def get_tutor() -> Agent[TutorDeps, str]:
    return make_tutor()


def get_lesson(request: Request, lesson_id: str) -> Lesson:
    lesson: Lesson | None = request.app.state.lessons.get(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


def _wrap(text: str) -> str:
    """Mark learner text as data. Any marker-like text the learner typed is defused first."""
    return f"<<<USER>>>\n{defuse(text)}\n<<<END>>>"


def _plain(section_html: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", section_html)).strip()


def _misconceptions(lesson: Lesson, attempts: list[dict[str, Any]]) -> list[str]:
    seen: list[str] = []
    items = {q.id: q for q in lesson.quiz}
    for a in attempts:
        item = items.get(a["item_id"])
        if item is None or a["correct"]:
            continue
        for o in item.options:
            if o.text == a["answer"] and o.misconception and o.misconception not in seen:
                seen.append(o.misconception)
    return seen[-5:]


def _render(text: str) -> str:
    """Markdown to HTML (html=False): each valid [§id] marker becomes a section link, each valid
    [src:N] marker a plain [N] that matches the numbered link in the Sources line."""
    text = re.sub(r"\[§([a-z0-9-]+)\]", r"[§\1](#\1)", text)
    return str(render_markdown(re.sub(r"\[src:(\d+)\]", r"\\[\1\\]", text)))


@router.post("/{lesson_id}", response_class=EventSourceResponse)
async def chat(
    lesson_id: str,
    body: ChatIn,
    request: Request,
    lesson: Annotated[Lesson, Depends(get_lesson)],
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> AsyncIterable[ServerSentEvent]:
    sources: dict[str, Source] = request.app.state.sources
    attempts = store.attempts_for(user_id, lesson_id)
    revealed = bool(store.events_for(user_id, "reveal", lesson_id))
    ceiling = compute_ceiling(len(attempts), body.active_item is not None, revealed)
    stored = store.chat_history(user_id, lesson_id, limit=10)
    hits = await retrieval.retrieve_async(body.message, track=lesson.track, k=settings.rag_k)
    log.info(
        "tutor turn lesson=%s retrieved=%d citations=%s",
        lesson_id,
        len(hits),
        [h.citation for h in hits],
    )  # never the chunk text
    deps = TutorDeps(
        lesson_title=lesson.title,
        sections=[(s.id, s.title, _plain(s.html)) for s in lesson.sections],
        ceiling=ceiling,
        attempts=len(attempts),
        misconceptions=_misconceptions(lesson, attempts),
        escalate=no_progress([*stored, {"role": "user", "content": body.message}]),
        n_sources=len(hits),
    )
    history: list[ModelMessage] = [
        ModelRequest(parts=[UserPromptPart(_wrap(m["content"]))])
        if m["role"] == "user"
        # [src:N] numbers belong to the turn that made them; this turn's N means other chunks.
        else ModelResponse(parts=[TextPart(number_sources(m["content"]))])
        for m in stored
    ]
    # Docs change every turn: they go in the learner's turn, not the cached instructions.
    prompt = f"{format_sources(hits)}\n\n{_wrap(body.message)}" if hits else _wrap(body.message)
    parts: list[str] = []
    try:
        async with get_tutor().run_stream(prompt, deps=deps, message_history=history) as result:
            async for delta in result.stream_text(delta=True):
                parts.append(delta)
                if ceiling >= 4:  # below L4 the learner sees only the filtered final html
                    yield ServerSentEvent(event="token", data=delta)
    except Exception:
        log.exception("tutor run failed")
        yield ServerSentEvent(event="error", data="The tutor failed, please retry.")
        return
    text, cited = validate_citations(
        apply_ceiling("".join(parts), ceiling), {s.id for s in lesson.sections}
    )
    text, used = validate_sources(text, len(hits))
    first = sources.get(lesson.sources[0]) if lesson.sources else None
    source_url = first.url if first else ""
    titles = {s.id: s.title for s in lesson.sections}
    citations: list[dict[str, Any]] = [
        {"id": i, "title": titles[i], "href": f"#{i}", "source_url": source_url} for i in cited
    ]
    citations += [{"n": n, "title": hits[n - 1].title, "url": hits[n - 1].citation} for n in used]
    yield ServerSentEvent(event="ceiling", data=f"L{ceiling}")
    yield ServerSentEvent(event="html", data=_render(text))
    yield ServerSentEvent(event="citations", data=citations)
    store.add_chat(user_id, lesson_id, "user", body.message, None, None)
    store.add_chat(user_id, lesson_id, "assistant", text, f"L{ceiling}", json.dumps(citations))


@router.get("/{lesson_id}/history")
def history(
    lesson_id: str,
    _: Annotated[Lesson, Depends(get_lesson)],
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in store.chat_history(user_id, lesson_id):
        if m["role"] == "user":
            out.append({"role": "user", "text": m["content"]})
        else:
            out.append(
                {
                    "role": "assistant",
                    "html": _render(m["content"]),
                    "ceiling": m["ceiling"],
                    "citations": json.loads(m["citations_json"] or "[]"),
                }
            )
    return out


@router.post("/{lesson_id}/reveal")
def reveal(
    lesson_id: str,
    body: RevealIn,
    lesson: Annotated[Lesson, Depends(get_lesson)],
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, str]:
    answer: str | None = None
    dues: list[str] = []
    for q in lesson.deeper:
        if q.id == body.item_id:
            answer = q.model_answer
            dues = [
                record_result(
                    store, user_id, lesson_id, criterion_item_id(q.id, c.name), Rating.Again
                )
                for c in q.rubric
            ]
    for item in lesson.quiz:
        if item.id == body.item_id:
            dues = [record_result(store, user_id, lesson_id, item.id, Rating.Again, surprise=True)]
            answer = (
                next((o.text for o in item.options if o.correct), "")
                if item.type == "single"
                else " → ".join(item.steps)
                if item.type == "order"
                else item.answer
            )
    if answer is None:
        raise HTTPException(status_code=404, detail="Item not found")
    store.log_event(
        user_id, "reveal", json.dumps({"lesson_id": lesson_id, "item_id": body.item_id})
    )
    return {"item_id": body.item_id, "answer": answer, "next_due": min(dues)}
