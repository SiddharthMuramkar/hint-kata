import json
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.content import Lesson
from app.deps import get_store, get_user_id
from app.quiz import grade_item, score, scramble
from app.store import Store

router = APIRouter(prefix="/api/quiz")


class Submission(BaseModel):
    answer: int | str | list[int]
    confidence: Literal["sure", "thinkso", "guessing"]
    try_no: int
    elapsed_ms: int = Field(ge=0)


def _lesson(request: Request, lesson_id: str) -> Lesson:
    lesson: Lesson | None = request.app.state.lessons.get(lesson_id)
    if lesson is None:
        raise HTTPException(404, "Lesson not found")
    return lesson


@router.get("/{lesson_id}")
def get_quiz(
    request: Request,
    lesson_id: str,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    lesson = _lesson(request, lesson_id)
    attempts = store.attempts_for(user_id, lesson_id)
    items = []
    for q in lesson.quiz:
        mine = [a for a in attempts if a["item_id"] == q.id]
        first = next((a for a in mine if a["try_no"] == 1), None)
        items.append(
            {
                "id": q.id,
                "type": q.type,
                "prompt": q.prompt,
                "options": [o.text for o in q.options],
                "steps": [q.steps[i] for i in scramble(q)],
                "answered": bool(mine),
                "correct_first_try": bool(first["correct"]) if first else None,
            }
        )
    return {"items": items, "score": score(attempts, lesson.quiz)}


@router.post("/{lesson_id}/{item_id}")
def post_quiz(
    request: Request,
    lesson_id: str,
    item_id: str,
    body: Submission,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    lesson = _lesson(request, lesson_id)
    item = next((q for q in lesson.quiz if q.id == item_id), None)
    if item is None:
        raise HTTPException(404, "Quiz item not found")
    mine = {
        a["try_no"]: a for a in store.attempts_for(user_id, lesson_id) if a["item_id"] == item_id
    }
    if body.try_no not in (1, 2) or body.try_no in mine:
        raise HTTPException(409, "That try is not allowed or was already used")
    if body.try_no == 2 and (1 not in mine or mine[1]["correct"]):
        raise HTTPException(409, "A second try only follows a wrong first try")
    r = grade_item(item, body.answer)
    store.add_attempt(
        user_id,
        lesson_id,
        item_id,
        "quiz",
        json.dumps(body.answer),
        r.correct,
        body.confidence,
        body.try_no,
        body.elapsed_ms,
    )
    attempts = store.attempts_for(user_id, lesson_id)
    answered = {a["item_id"] for a in attempts}
    return {
        "correct": r.correct,
        "feedback": r.feedback,
        "misconception": r.misconception,
        "explanation": r.explanation,
        "correct_answer": r.correct_answer if r.correct or body.try_no == 2 else None,
        "surprise": body.confidence == "sure" and not r.correct,
        "score": score(attempts, lesson.quiz),
        "done": all(q.id in answered for q in lesson.quiz),
    }
