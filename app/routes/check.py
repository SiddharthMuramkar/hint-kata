from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.checker import run_check
from app.config import settings
from app.deps import get_store, get_user_id
from app.store import Store

router = APIRouter(prefix="/api/check")


@router.post("/{lesson_id}")
def post_check(
    lesson_id: str,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    r = run_check(lesson_id, settings, store, user_id)
    return {"passed": r.passed, "output": r.output, "kind": r.kind}


@router.get("/{lesson_id}")
def get_check(
    lesson_id: str,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]:
    row = store.last_check(user_id, lesson_id)
    if row is None:
        return {"passed": None}
    return {"passed": bool(row["passed"]), "output": row["output"]}
