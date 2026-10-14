from typing import Any

from fastapi import FastAPI

app = FastAPI()

# The store keeps the FULL record of each user, password included.
USERS: dict[int, dict[str, Any]] = {}
STOCK: dict[str, int] = {"apple": 2, "pear": 0}


# TODO 1: write two Pydantic models.
#   UserIn:  name: str, email: str, password: str
#   UserOut: id: int, name: str, email: str   (no password!)


# TODO 2: use the models in this route.
#   - take a `UserIn` as the body, instead of a plain dict
#   - answer with status 201 (status.HTTP_201_CREATED)
#   - make sure the response is a `UserOut`, so FastAPI filters out the password
@app.post("/users/")
def create_user(user: dict[str, str]):
    new_id = max(USERS, default=0) + 1
    USERS[new_id] = {"id": new_id, **user}
    return USERS[new_id]


# TODO 3: answer with a `UserOut`. For an unknown id, raise HTTPException with
#   status 404 and detail="user not found" instead of returning None.
@app.get("/users/{user_id}")
def read_user(user_id: int):
    return USERS.get(user_id)


# TODO 4: define the exception class `OutOfStock` (it keeps the item name in `self.item`),
#   then register a handler with @app.exception_handler(OutOfStock) that returns a
#   JSONResponse with status 409 and {"detail": "<item> is out of stock"}.
@app.post("/orders/{item}")
def order(item: str) -> dict[str, str]:
    if STOCK.get(item, 0) <= 0:
        raise OutOfStock(item)  # noqa: F821
    STOCK[item] -= 1
    return {"ordered": item}


# TODO 5: register a handler for RequestValidationError. Keep status 422 and return
#   {"detail": [{"loc": [...], "msg": "..."}]}, with only `loc` and `msg` for each error
#   from exc.errors(). Do not include `input`: it can hold the password.
