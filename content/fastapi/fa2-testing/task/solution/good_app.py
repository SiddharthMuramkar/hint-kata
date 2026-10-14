"""The correct app. Your tests must PASS against this one. Do not edit it."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

ITEMS: dict[int, dict] = {1: {"id": 1, "name": "Widget", "price": 9.99}}


class Item(BaseModel):
    id: int
    name: str
    price: float = Field(gt=0)  # a price must be above zero


@app.get("/items/{item_id}")
def read_item(item_id: int) -> dict:
    if item_id not in ITEMS:
        raise HTTPException(status_code=404, detail="Item not found")
    return ITEMS[item_id]


@app.post("/items/", status_code=201)
def create_item(item: Item) -> dict:
    ITEMS[item.id] = item.model_dump()
    return ITEMS[item.id]
