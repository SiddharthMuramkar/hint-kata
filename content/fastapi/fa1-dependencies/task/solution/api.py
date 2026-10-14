from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, Query

app = FastAPI()

LOG: list[str] = []
ITEMS = [f"item-{n}" for n in range(25)]


def pagination(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> dict[str, int]:
    return {"skip": skip, "limit": limit}


def get_db() -> Iterator[list[str]]:
    LOG.append("open")
    try:
        yield ITEMS
    finally:
        LOG.append("close")


@app.get("/items/")
def list_items(
    page: Annotated[dict[str, int], Depends(pagination)],
    db: Annotated[list[str], Depends(get_db)],
):
    skip, limit = page["skip"], page["limit"]
    return {"skip": skip, "limit": limit, "items": db[skip : skip + limit]}
