from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException

from app.checker import run_check, valid_lesson_id
from app.config import settings
from app.deps import get_store, get_user_id
from app.store import Store

router = APIRouter(prefix="/api/check")


def _require_valid(lesson_id: str) -> None:
    if not valid_lesson_id(lesson_id):
        raise HTTPException(status_code=404)


@router.post("/{lesson_id}")
def post_check(
    lesson_id: str,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    _require_valid(lesson_id)
    r = run_check(lesson_id, settings, store, user_id)
    return {"passed": r.passed, "output": r.output, "kind": r.kind}


@router.get("/{lesson_id}")
def get_check(
    lesson_id: str,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    _require_valid(lesson_id)
    row = store.last_check(user_id, lesson_id)
    if row is None:
        return {"passed": None}
    return {"passed": bool(row["passed"]), "output": row["output"]}
