# Task: an order API with nested models

Open `workspace/fa3-request-bodies/api.py`. It has a small FastAPI app with two stub routes. They answer, but they do not read any body yet. Your job is to describe the order data with Pydantic models and use them.

## 1. Three models

- `Address` has `street: str` and `city: str`. Both are required.
- `LineItem` has `sku: str`, `unit_price: float` and `quantity: int`. The quantity must be greater than `0`. Put that rule on the field with `Field`.
- `Order` has `customer: Address`, `items: list[LineItem]` and `note: str | None = None`.

Use these exact class names. The hidden tests look for them in the OpenAPI schema.

## 2. `POST /orders/`

Take an `Order` as the body. Answer with status `201` and this JSON:

```json
{"total": 10.0, "item_count": 2}
```

`total` is the sum of `unit_price * quantity` over all items, rounded to 2 decimals. `item_count` is the number of line items. Set the status with the `status_code` argument of the decorator.

## 3. `PUT /orders/{order_id}`

This route mixes all three kinds of parameters:

- `order_id` comes from the path and is an `int`.
- `order` is the same `Order` model, read from the body. Send the fields directly. Do not embed.
- `dry_run` is a `bool` query parameter that defaults to `False`.

It answers `200` with `{"order_id": ..., "total": ..., "dry_run": ...}`. Compute `total` the same way as above. Write the sum once in a small helper and call it from both routes.

## Check your work

The hidden tests use a test client. They send valid and invalid orders and check the status codes and the `loc` of every `422`. A bad quantity in the second line item must report `["body", "items", 1, "quantity"]`. A missing city must report `["body", "customer", "city"]`. If a `loc` looks different, check which parameter FastAPI thinks the model is.
