from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.traces import grade, load_trace, public_view

router = APIRouter(prefix="/api/trace")


class Choice(BaseModel):
    choice: int


@router.get("/{lesson_id}")
async def get_trace(lesson_id: str) -> dict[str, object]:
    trace = load_trace(lesson_id)
    if trace is None:
        raise HTTPException(404, "No trace for this lesson")
    return public_view(trace)


@router.post("/{lesson_id}/{step_idx}")
async def answer_checkpoint(lesson_id: str, step_idx: int, body: Choice) -> dict[str, object]:
    trace = load_trace(lesson_id)
    if trace is None:
        raise HTTPException(404, "No trace for this lesson")
    try:
        correct, explanation = grade(trace, step_idx, body.choice)
    except KeyError:
        raise HTTPException(404, "No checkpoint at this step") from None
    return {"correct": correct, "explanation": explanation}
