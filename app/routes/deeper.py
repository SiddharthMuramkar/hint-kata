from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from app.agents.grader import MAX_ANSWER_CHARS, GradeOutcome, grade_answer
from app.content import DeeperQuestion
from app.deps import get_store, get_user_id
from app.store import Store

router = APIRouter(prefix="/api/deeper")
MAX_ATTEMPTS = 3  # the first try plus 2 revisions


class AnswerIn(BaseModel):
    answer: str


def _question(request: Request, lesson_id: str, question_id: str) -> DeeperQuestion:
    lesson = request.app.state.lessons.get(lesson_id)
    for q in lesson.deeper if lesson else []:
        if q.id == question_id:
            return q
    raise HTTPException(status_code=404, detail="Question not found")


def _view(q: DeeperQuestion, attempt_no: int, o: GradeOutcome) -> dict[str, Any]:
    done = o.all_met or attempt_no >= MAX_ATTEMPTS
    return {
        "attempt_no": attempt_no,
        **o.model_dump(),
        "model_answer": q.model_answer if done else None,
        "can_retry": not done,
    }


@router.post("/{lesson_id}/{question_id}")
async def post_deeper(
    request: Request,
    lesson_id: str,
    question_id: str,
    body: AnswerIn,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    q = _question(request, lesson_id, question_id)
    rows = store.grades_for(user_id, lesson_id, question_id)
    attempt_no = len(rows) + 1
    if attempt_no > MAX_ATTEMPTS or (
        rows and GradeOutcome.model_validate_json(rows[-1]["result_json"]).all_met
    ):
        raise HTTPException(status_code=409, detail="No attempts left")
    answer = body.answer[:MAX_ANSWER_CHARS]
    outcome = await grade_answer(q, answer)
    store.add_grade(
        user_id,
        lesson_id,
        question_id,
        attempt_no,
        answer,
        outcome.model_dump_json(),
        outcome.flagged,
    )
    return _view(q, attempt_no, outcome)


@router.get("/{lesson_id}/{question_id}")
def get_deeper(
    request: Request,
    lesson_id: str,
    question_id: str,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> list[dict[str, Any]]:
    q = _question(request, lesson_id, question_id)
    rows = store.grades_for(user_id, lesson_id, question_id)
    return [
        _view(q, r["attempt_no"], GradeOutcome.model_validate_json(r["result_json"])) for r in rows
    ]
