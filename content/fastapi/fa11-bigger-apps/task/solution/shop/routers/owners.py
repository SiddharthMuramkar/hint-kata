from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/owners", tags=["owners"])

OWNERS = {1: {"name": "Ana"}}


@router.get("/")
def list_owners() -> dict[int, dict[str, str]]:
    return OWNERS


@router.get("/{owner_id}")
def read_owner(owner_id: int) -> dict[str, str]:
    if owner_id not in OWNERS:
        raise HTTPException(status_code=404, detail="Owner not found")
    return OWNERS[owner_id]
