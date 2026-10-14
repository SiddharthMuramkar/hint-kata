import copy

import api  # ty: ignore[unresolved-import]  # the learner's api.py, on PYTHONPATH
import pytest
from fastapi.testclient import TestClient

GOOD = {
    "customer": {"street": "1 Main St", "city": "Springfield"},
    "items": [
        {"sku": "tea", "unit_price": 2.5, "quantity": 2},
        {"sku": "cup", "unit_price": 1.25, "quantity": 4},
    ],
}


@pytest.fixture
def client():
    return TestClient(api.app)


def order(**changes):
    body = copy.deepcopy(GOOD)
    body.update(changes)
    return body


def locs(response):
    return [error["loc"] for error in response.json()["detail"]]


def test_valid_order_is_created(client):
    response = client.post("/orders/", json=GOOD)
    assert response.status_code == 201
    assert response.json() == {"total": 10.0, "item_count": 2}


def test_note_is_optional_and_allowed(client):
    assert client.post("/orders/", json=order(note="leave at door")).status_code == 201
    assert client.post("/orders/", json=order(note=None)).status_code == 201


def test_total_is_rounded_to_two_decimals(client):
    items = [{"sku": "x", "unit_price": 0.1, "quantity": 3}]
    response = client.post("/orders/", json=order(items=items))
    assert response.json()["total"] == 0.3


def test_negative_quantity_reports_its_loc(client):
    items = copy.deepcopy(GOOD["items"])
    items[0]["quantity"] = -1
    response = client.post("/orders/", json=order(items=items))
    assert response.status_code == 422
    assert locs(response) == [["body", "items", 0, "quantity"]]


def test_zero_quantity_in_second_item_reports_its_position(client):
    items = copy.deepcopy(GOOD["items"])
    items[1]["quantity"] = 0
    response = client.post("/orders/", json=order(items=items))
    assert response.status_code == 422
    assert locs(response) == [["body", "items", 1, "quantity"]]


def test_missing_nested_field_reports_the_full_path(client):
    customer = {"street": "1 Main St"}
    response = client.post("/orders/", json=order(customer=customer))
    assert response.status_code == 422
    assert locs(response) == [["body", "customer", "city"]]


def test_missing_items_is_rejected(client):
    body = order()
    del body["items"]
    response = client.post("/orders/", json=body)
    assert response.status_code == 422
    assert locs(response) == [["body", "items"]]


def test_wrong_type_in_a_line_item_is_rejected(client):
    items = copy.deepcopy(GOOD["items"])
    items[0]["quantity"] = "lots"
    response = client.post("/orders/", json=order(items=items))
    assert response.status_code == 422
    assert locs(response) == [["body", "items", 0, "quantity"]]


def test_all_problems_are_reported_together(client):
    items = copy.deepcopy(GOOD["items"])
    items[0]["quantity"] = 0
    response = client.post("/orders/", json=order(items=items, customer={"city": "X"}))
    assert response.status_code == 422
    assert sorted(map(str, locs(response))) == sorted(
        map(str, [["body", "customer", "street"], ["body", "items", 0, "quantity"]])
    )


def test_form_data_is_not_a_json_body(client):
    response = client.post("/orders/", data={"customer": "x"})
    assert response.status_code == 422
    assert locs(response) == [["body"]]


def test_put_mixes_path_query_and_body(client):
    response = client.put("/orders/7", json=GOOD, params={"dry_run": "true"})
    assert response.status_code == 200
    assert response.json() == {"order_id": 7, "total": 10.0, "dry_run": True}


def test_put_dry_run_defaults_to_false(client):
    response = client.put("/orders/7", json=GOOD)
    assert response.status_code == 200
    assert response.json()["dry_run"] is False


def test_put_bad_path_value_reports_a_path_loc(client):
    response = client.put("/orders/abc", json=GOOD)
    assert response.status_code == 422
    assert locs(response) == [["path", "order_id"]]


def test_put_bad_query_value_reports_a_query_loc(client):
    response = client.put("/orders/7", json=GOOD, params={"dry_run": "maybe"})
    assert response.status_code == 422
    assert locs(response) == [["query", "dry_run"]]


def test_put_body_errors_have_a_plain_body_loc(client):
    items = copy.deepcopy(GOOD["items"])
    items[0]["quantity"] = -3
    response = client.put("/orders/7", json=order(items=items))
    assert response.status_code == 422
    assert locs(response) == [["body", "items", 0, "quantity"]]


def test_models_show_up_in_the_openapi_schema(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert {"Order", "Address", "LineItem"} <= set(schemas)
    assert schemas["LineItem"]["properties"]["quantity"]["exclusiveMinimum"] == 0
    assert schemas["Order"]["properties"]["items"]["items"] == {"$ref": "#/components/schemas/LineItem"}
