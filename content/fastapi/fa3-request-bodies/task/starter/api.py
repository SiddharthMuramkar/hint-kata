from fastapi import FastAPI

app = FastAPI()


# TODO 1: add the models (import BaseModel and Field from pydantic).
#   Address:  street: str, city: str
#   LineItem: sku: str, unit_price: float, quantity: int with Field(gt=0)
#   Order:    customer: Address, items: list[LineItem], note: str | None = None


# TODO 2: write a helper `order_total(order)` that returns the sum of
#   unit_price * quantity over order.items, rounded to 2 decimals.


# TODO 3: make this route take an `Order` body, answer with status 201, and return
#   {"total": <order_total>, "item_count": <number of items>}.
@app.post("/orders/")
def create_order():
    return {"total": 0, "item_count": 0}


# TODO 4: make this route take `order_id` from the path, an `Order` from the body (not embedded)
#   and a `dry_run: bool = False` query parameter. Return
#   {"order_id": ..., "total": <order_total>, "dry_run": ...}.
@app.put("/orders/{order_id}")
def replace_order(order_id: int):
    return {"order_id": order_id, "total": 0, "dry_run": False}
