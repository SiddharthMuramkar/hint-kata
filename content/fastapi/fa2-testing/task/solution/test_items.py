import importlib
import os

from fastapi.testclient import TestClient

# The checker runs this file twice: once with APP_MODULE=good_app, once with APP_MODULE=buggy_app.
app = importlib.import_module(os.environ.get("APP_MODULE", "good_app")).app
client = TestClient(app)


def test_read_known_item() -> None:
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Widget", "price": 9.99}


def test_unknown_item_is_404() -> None:
    response = client.get("/items/9999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}


def test_create_item_then_read_it_back() -> None:
    new_item = {"id": 50, "name": "Gadget", "price": 4.5}
    created = client.post("/items/", json=new_item)
    assert created.status_code == 201
    assert created.json() == new_item
    assert client.get("/items/50").json() == new_item


def test_negative_price_is_rejected() -> None:
    response = client.post("/items/", json={"id": 51, "name": "Bad", "price": -1})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "price"]


def test_missing_name_is_rejected() -> None:
    response = client.post("/items/", json={"id": 52, "price": 3})
    assert response.status_code == 422
