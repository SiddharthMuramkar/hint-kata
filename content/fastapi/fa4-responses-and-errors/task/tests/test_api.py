import api  # ty: ignore[unresolved-import]  # the learner's api.py, on PYTHONPATH
import pytest
from fastapi.testclient import TestClient

PASSWORD = "s3cret-pw-123"
NEW_USER = {"name": "Ann", "email": "ann@example.com", "password": PASSWORD}


@pytest.fixture
def client():
    api.USERS.clear()
    api.STOCK.clear()
    api.STOCK.update({"apple": 2, "pear": 0})
    # Errors in the learner's code should show up as a failed assert, not as a crash.
    yield TestClient(api.app, raise_server_exceptions=False)
    api.USERS.clear()


def test_create_user_is_201_and_has_no_password(client):
    response = client.post("/users/", json=NEW_USER)
    assert response.status_code == 201
    assert response.json() == {"id": 1, "name": "Ann", "email": "ann@example.com"}


def test_output_model_has_no_password_field():
    assert "password" not in api.UserOut.model_fields


def test_create_route_documents_user_out_with_201():
    # The route must be declared with the output model, not filter by hand.
    schema = api.app.openapi()["paths"]["/users/"]["post"]["responses"]["201"]
    assert schema["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/UserOut"
    }


def test_password_is_not_in_the_create_response(client):
    response = client.post("/users/", json=NEW_USER)
    assert PASSWORD not in response.text
    assert "password" not in response.text


def test_password_is_not_in_the_read_response(client):
    client.post("/users/", json=NEW_USER)
    response = client.get("/users/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "Ann", "email": "ann@example.com"}
    assert PASSWORD not in response.text


def test_the_store_still_keeps_the_password(client):
    # The model filters the response. It must not change what is stored.
    client.post("/users/", json=NEW_USER)
    assert api.USERS[1]["password"] == PASSWORD


def test_ids_count_up(client):
    client.post("/users/", json=NEW_USER)
    second = client.post("/users/", json={**NEW_USER, "name": "Bo"})
    assert second.json()["id"] == 2
    assert client.get("/users/2").json()["name"] == "Bo"


def test_unknown_user_is_404_with_detail(client):
    response = client.get("/users/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "user not found"}


def test_order_in_stock_works_and_uses_up_stock(client):
    response = client.post("/orders/apple")
    assert response.status_code == 200
    assert response.json() == {"ordered": "apple"}
    assert api.STOCK["apple"] == 1


def test_out_of_stock_is_409_with_detail(client):
    response = client.post("/orders/pear")
    assert response.status_code == 409
    assert response.json() == {"detail": "pear is out of stock"}


def test_exception_class_keeps_the_item_name():
    assert api.OutOfStock("kiwi").item == "kiwi"


def test_missing_field_is_422_with_a_short_body(client):
    response = client.post("/users/", json={"name": "Ann", "password": PASSWORD})
    assert response.status_code == 422
    assert response.json() == {"detail": [{"loc": ["body", "email"], "msg": "Field required"}]}


def test_password_is_not_echoed_in_a_422(client):
    response = client.post("/users/", json={"name": "Ann", "password": PASSWORD})
    assert PASSWORD not in response.text


def test_wrong_type_is_422(client):
    response = client.post("/users/", json={**NEW_USER, "name": ["not", "a", "string"]})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "name"]
    assert PASSWORD not in response.text


def test_bad_path_value_is_422(client):
    response = client.get("/users/abc")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "user_id"]
