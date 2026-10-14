from enum import Enum

import api  # the learner's api.py, on PYTHONPATH
import pytest
from fastapi.testclient import TestClient

client = TestClient(api.app)


def locs(response) -> list[list]:
    return [e["loc"] for e in response.json()["detail"]]


def test_book_id_is_converted_to_an_int():
    response = client.get("/books/3")
    assert response.status_code == 200
    assert response.json() == {"book_id": 3}  # a JSON number, not the text "3"


@pytest.mark.parametrize("value", ["abc", "4.2"])
def test_book_id_that_is_not_an_integer_is_a_422_on_the_path(value):
    response = client.get(f"/books/{value}")
    assert response.status_code == 422
    assert locs(response) == [["path", "book_id"]]


def test_book_id_must_be_at_least_1():
    assert client.get("/books/1").status_code == 200
    for value in ("0", "-5"):
        response = client.get(f"/books/{value}")
        assert response.status_code == 422
        assert locs(response) == [["path", "book_id"]]


def test_featured_is_not_captured_by_the_variable_route():
    response = client.get("/books/featured")
    assert response.status_code == 200, "is /books/featured declared before /books/{book_id}?"
    assert response.json() == {"featured": "Dune"}


def test_shelf_is_a_str_enum_with_three_members():
    assert issubclass(api.Shelf, str) and issubclass(api.Shelf, Enum)
    assert {m.value for m in api.Shelf} == {"fiction", "science", "history"}


@pytest.mark.parametrize("shelf", ["fiction", "science", "history"])
def test_each_shelf_value_is_accepted(shelf):
    response = client.get(f"/shelves/{shelf}")
    assert response.status_code == 200
    assert response.json() == {"shelf": shelf}


def test_unknown_shelf_is_a_422_on_the_path():
    for value in ("poetry", "Fiction"):
        response = client.get(f"/shelves/{value}")
        assert response.status_code == 422
        assert locs(response) == [["path", "shelf"]]


def test_q_is_required():
    response = client.get("/search")
    assert response.status_code == 422
    assert locs(response) == [["query", "q"]]
    assert response.json()["detail"][0]["type"] == "missing"


def test_optional_parameters_have_their_defaults():
    response = client.get("/search", params={"q": "dune"})
    assert response.status_code == 200
    assert response.json() == {
        "q": "dune",
        "tags": None,
        "limit": 10,
        "sort": "title",
        "in_stock": False,
    }


@pytest.mark.parametrize(
    ("q", "ok"),
    [("ab", False), ("abc", True), ("a" * 20, True), ("a" * 21, False)],
)
def test_q_length_is_between_3_and_20(q, ok):
    response = client.get("/search", params={"q": q})
    if ok:
        assert response.status_code == 200
    else:
        assert response.status_code == 422
        assert locs(response) == [["query", "q"]]


def test_tags_collects_repeated_values_into_a_list():
    response = client.get("/search?q=dune&tags=a&tags=b")
    assert response.status_code == 200
    assert response.json()["tags"] == ["a", "b"]
    assert client.get("/search?q=dune&tags=a").json()["tags"] == ["a"]


@pytest.mark.parametrize(("limit", "ok"), [(0, False), (1, True), (50, True), (51, False)])
def test_limit_is_between_1_and_50(limit, ok):
    response = client.get("/search", params={"q": "dune", "limit": limit})
    if ok:
        assert response.status_code == 200
        assert response.json()["limit"] == limit
    else:
        assert response.status_code == 422
        assert locs(response) == [["query", "limit"]]


def test_sort_must_be_exactly_title_or_year():
    assert client.get("/search", params={"q": "dune", "sort": "year"}).json()["sort"] == "year"
    for value in ("price", "xtitle", "title-x"):
        response = client.get("/search", params={"q": "dune", "sort": value})
        assert response.status_code == 422, value
        assert locs(response) == [["query", "sort"]]


def test_in_stock_is_converted_to_a_bool():
    assert client.get("/search?q=dune&in_stock=yes").json()["in_stock"] is True
    assert client.get("/search?q=dune&in_stock=0").json()["in_stock"] is False
    response = client.get("/search?q=dune&in_stock=maybe")
    assert response.status_code == 422
    assert locs(response) == [["query", "in_stock"]]


def test_all_errors_come_back_together():
    response = client.get("/search", params={"limit": 0, "sort": "price"})
    assert response.status_code == 422
    assert sorted(locs(response)) == [["query", "limit"], ["query", "q"], ["query", "sort"]]
