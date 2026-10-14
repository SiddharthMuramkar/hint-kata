from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from app.checker import run_check, valid_lesson_id
from app.config import settings
from app.deps import get_store, get_user_id
from app.store import Store

router = APIRouter(prefix="/api/check")


def _require_valid(request: Request, lesson_id: str) -> None:
    """404 unless the id is well formed (checked first) and names a loaded lesson."""
    if not valid_lesson_id(lesson_id) or lesson_id not in request.app.state.lessons:
        raise HTTPException(status_code=404)


@router.post("/{lesson_id}")
def post_check(
    request: Request,
    lesson_id: str,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    _require_valid(request, lesson_id)
    r = run_check(lesson_id, settings, store, user_id)
    return {"passed": r.passed, "output": r.output, "kind": r.kind}


@router.get("/{lesson_id}")
def get_check(
    request: Request,
    lesson_id: str,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    _require_valid(request, lesson_id)
    row = store.last_check(user_id, lesson_id)
    if row is None:
        return {"passed": None}
    return {"passed": bool(row["passed"]), "output": row["output"]}
