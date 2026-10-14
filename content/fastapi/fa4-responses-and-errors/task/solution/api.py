from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()

# The store keeps the FULL record of each user, password included.
USERS: dict[int, dict[str, Any]] = {}
STOCK: dict[str, int] = {"apple": 2, "pear": 0}


class UserIn(BaseModel):
    name: str
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str


@app.post("/users/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserIn) -> Any:
    new_id = max(USERS, default=0) + 1
    USERS[new_id] = {"id": new_id, **user.model_dump()}
    return USERS[new_id]  # still holds the password; UserOut filters it out


@app.get("/users/{user_id}", response_model=UserOut)
def read_user(user_id: int) -> Any:
    if user_id not in USERS:
        raise HTTPException(status_code=404, detail="user not found")
    return USERS[user_id]


class OutOfStock(Exception):
    def __init__(self, item: str) -> None:
        self.item = item


@app.exception_handler(OutOfStock)
def out_of_stock_handler(request: Request, exc: OutOfStock) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": f"{exc.item} is out of stock"})


@app.post("/orders/{item}")
def order(item: str) -> dict[str, str]:
    if STOCK.get(item, 0) <= 0:
        raise OutOfStock(item)
    STOCK[item] -= 1
    return {"ordered": item}


@app.exception_handler(RequestValidationError)
def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Only `loc` and `msg`: the default body also has `input`, which can hold the password.
    problems = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": problems})
