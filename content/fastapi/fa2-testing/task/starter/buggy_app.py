"""A broken copy of good_app. Your tests must FAIL against this one. Do not edit it."""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

ITEMS: dict[int, dict] = {1: {"id": 1, "name": "Widget", "price": 9.99}}


class Item(BaseModel):
    id: int
    name: str
    price: float  # bug: the "price above zero" rule is missing


@app.get("/items/{item_id}")
def read_item(item_id: int) -> dict:
    # bug: an unknown id gives 200 and an empty body instead of 404
    return ITEMS.get(item_id, {})


@app.post("/items/", status_code=201)
def create_item(item: Item) -> dict:
    ITEMS[item.id] = item.model_dump()
    return ITEMS[item.id]
