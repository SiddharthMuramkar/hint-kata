from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI()


class Address(BaseModel):
    street: str
    city: str


class LineItem(BaseModel):
    sku: str
    unit_price: float
    quantity: int = Field(gt=0)


class Order(BaseModel):
    customer: Address
    items: list[LineItem]
    note: str | None = None


def order_total(order: Order) -> float:
    return round(sum(item.unit_price * item.quantity for item in order.items), 2)


@app.post("/orders/", status_code=201)
def create_order(order: Order):
    return {"total": order_total(order), "item_count": len(order.items)}


@app.put("/orders/{order_id}")
def replace_order(order_id: int, order: Order, dry_run: bool = False):
    return {"order_id": order_id, "total": order_total(order), "dry_run": dry_run}
