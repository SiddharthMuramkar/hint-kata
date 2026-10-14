import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.config import settings
from app.deps import get_store, get_user_id
from app.quiz import grade_item, scramble
from app.review import DueItem, due_items, rating_for, record_result, resolve
from app.store import Store, open_store

router = APIRouter()


def _due_count(request: Request) -> dict[str, int]:
    """For the nav link: how many cards are due now (0 when there is no database yet)."""
    if not Path(settings.hintkata_db_path).exists():
        return {"due_count": 0}
    store = open_store(settings.hintkata_db_path)
    try:
        lessons = getattr(request.app.state, "lessons", {})
        due = due_items(store, lessons, store.ensure_user("owner"), datetime.now(UTC))
        return {"due_count": len(due)}
    finally:
        store.close()


templates = Jinja2Templates(
    directory=Path(__file__).parent.parent / "templates", context_processors=[_due_count]
)


class Review(BaseModel):
    answer: int | str | list[int] | None = None
    confidence: Literal["sure", "thinkso", "guessing"] = "thinkso"
    elapsed_ms: int = Field(default=0, ge=0)
    self_rating: Literal["good", "again"] | None = None


def _view(d: DueItem) -> dict[str, Any]:
    """What the browser may see: never the correct answer."""
    q = d.item
    return {
        "card_id": d.card_id,
        "lesson_id": d.lesson_id,
        "lesson_title": d.lesson_title,
        "item_id": d.item_id,
        "kind": d.kind,
        "prompt": d.prompt,
        "type": q.type if q else None,
        "options": [o.text for o in q.options] if q else [],
        "steps": [q.steps[i] for i in scramble(q)] if q else [],
        "criterion_text": d.criterion_text,
    }


@router.get("/api/review")
def api_review(
    request: Request,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> list[dict[str, Any]]:
    due = due_items(store, request.app.state.lessons, user_id, datetime.now(UTC))
    return [_view(d) for d in due]


@router.get("/today", response_class=HTMLResponse)
def today(
    request: Request,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> HTMLResponse:
    groups: dict[str, list[DueItem]] = {}
    for d in due_items(store, request.app.state.lessons, user_id, datetime.now(UTC)):
        groups.setdefault(d.lesson_id, []).append(d)
    return templates.TemplateResponse(
        request=request, name="today.html", context={"groups": groups}
    )


@router.post("/api/review/{card_id}")
def post_review(
    request: Request,
    card_id: int,
    body: Review,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    card = store.card_by_id(user_id, card_id)
    d = resolve(card, request.app.state.lessons) if card else None
    if d is None:
        raise HTTPException(404, "Card not found")
    if d.item is not None:
        if body.answer is None:
            raise HTTPException(422, "A quiz card needs an answer")
        r = grade_item(d.item, body.answer)
        correct, feedback = r.correct, r.feedback or r.explanation
    elif body.self_rating is None:
        raise HTTPException(422, "A criterion card needs self_rating")
    else:
        correct, feedback = body.self_rating == "good", ""
    rating = rating_for(correct, body.confidence, 1, False, body.elapsed_ms)
    due = record_result(
        store,
        user_id,
        d.lesson_id,
        d.item_id,
        rating,
        surprise=not correct and body.confidence == "sure",
    )
    store.add_attempt(
        user_id,
        d.lesson_id,
        d.item_id,
        "review",
        json.dumps(body.answer if body.answer is not None else body.self_rating),
        correct,
        body.confidence,
        1,
        body.elapsed_ms,
    )
    return {"correct": correct, "feedback": feedback, "next_due": due}
