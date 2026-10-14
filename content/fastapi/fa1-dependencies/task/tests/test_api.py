import api  # the learner's api.py, on PYTHONPATH
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    api.LOG.clear()
    api.app.dependency_overrides.clear()
    yield TestClient(api.app)
    api.app.dependency_overrides.clear()


def test_defaults(client):
    response = client.get("/items/")
    assert response.status_code == 200
    assert response.json() == {"skip": 0, "limit": 10, "items": api.ITEMS[0:10]}


def test_skip_and_limit_from_query(client):
    response = client.get("/items/", params={"skip": 5, "limit": 3})
    assert response.status_code == 200
    assert response.json() == {"skip": 5, "limit": 3, "items": api.ITEMS[5:8]}


def test_limit_above_100_is_rejected(client):
    assert client.get("/items/", params={"limit": 101}).status_code == 422
    assert client.get("/items/", params={"limit": 100}).status_code == 200


def test_other_bad_values_are_rejected(client):
    assert client.get("/items/", params={"limit": 0}).status_code == 422
    assert client.get("/items/", params={"skip": -1}).status_code == 422
    assert client.get("/items/", params={"skip": "abc"}).status_code == 422


def test_pagination_returns_a_dict():
    assert api.pagination(skip=3, limit=4) == {"skip": 3, "limit": 4}


def test_log_ends_with_close_after_a_request(client):
    assert client.get("/items/").status_code == 200
    assert api.LOG == ["open", "close"]


def test_each_request_opens_and_closes_once(client):
    client.get("/items/")
    client.get("/items/")
    assert api.LOG == ["open", "close", "open", "close"]


def test_route_uses_the_pagination_dependency(client):
    api.app.dependency_overrides[api.pagination] = lambda: {"skip": 1, "limit": 2}
    response = client.get("/items/")
    assert response.json() == {"skip": 1, "limit": 2, "items": api.ITEMS[1:3]}


def test_route_uses_the_get_db_dependency(client):
    api.app.dependency_overrides[api.get_db] = lambda: ["a", "b", "c"]
    response = client.get("/items/", params={"skip": 1, "limit": 5})
    assert response.json() == {"skip": 1, "limit": 5, "items": ["b", "c"]}
    # The fake replaced get_db, so the real one never ran.
    assert api.LOG == []
