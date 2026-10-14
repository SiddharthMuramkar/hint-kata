from fastapi import FastAPI

app = FastAPI()

LOG: list[str] = []
ITEMS = [f"item-{n}" for n in range(25)]


# TODO 1: write `pagination(skip, limit)` that returns {"skip": skip, "limit": limit}.
#   skip: int, default 0, must be >= 0.   limit: int, default 10, must be 1..100.
#   Let FastAPI validate it (for example with Query(ge=..., le=...)).


# TODO 2: write `get_db()`. Append "open" to LOG, yield ITEMS, and append "close" to LOG
#   in a `finally` block so it always runs.


# TODO 3: change the route below so it gets `page` from Depends(pagination) and `db` from
#   Depends(get_db) (use Annotated), then return the slice db[skip : skip + limit].
@app.get("/items/")
def list_items():
    return {"skip": 0, "limit": 10, "items": []}
