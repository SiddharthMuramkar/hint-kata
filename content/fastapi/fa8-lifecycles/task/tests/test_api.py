from typing import Annotated

import api  # the learner's api.py, on PYTHONPATH
import pytest
from fastapi import Depends, HTTPException, Request
from fastapi.testclient import TestClient

POOLS: list[api.FakePool] = []
_ROUTES_ADDED: list[bool] = []


def _add_test_routes() -> None:
    """Add routes to the learner's app. They use the learner's `get_conn`."""
    assert hasattr(api, "get_conn"), "api.py needs a dependency called get_conn (TODO 2)"

    @api.app.get("/_probe")
    def probe(request: Request) -> dict[str, str]:
        POOLS.append(request.state.pool)
        return {"pool": type(request.state.pool).__name__}

    @api.app.get("/_boom")
    def boom(conn: Annotated[api.FakeConnection, Depends(api.get_conn)]) -> None:
        api.EVENTS.append("route")
        raise RuntimeError("the route failed")

    @api.app.get("/_missing")
    def missing(conn: Annotated[api.FakeConnection, Depends(api.get_conn)]) -> None:
        api.EVENTS.append("route")
        raise HTTPException(status_code=404, detail="no such row")

    _ROUTES_ADDED.append(True)


@pytest.fixture(autouse=True)
def clean_state() -> None:
    if not _ROUTES_ADDED:
        _add_test_routes()
    api.EVENTS.clear()
    POOLS.clear()


def test_the_pool_opens_at_start_up_not_at_import():
    client = TestClient(api.app)  # no `with`: the lifespan has not started
    assert api.EVENTS == []
    with client:
        assert api.EVENTS == ["open"], "the lifespan should open the pool before the first request"


def test_events_for_one_request_in_order():
    with TestClient(api.app) as client:
        response = client.get("/rows")
        assert response.status_code == 200
        assert response.json() == {"rows": ["result of select 1"]}
        assert api.EVENTS == ["open", "checkout", "route", "release"]
    assert api.EVENTS == ["open", "checkout", "route", "release", "close"]


def test_the_pool_opens_once_and_each_request_borrows_its_own_connection():
    with TestClient(api.app) as client:
        for _ in range(3):
            assert client.get("/rows").status_code == 200
    assert api.EVENTS == ["open"] + ["checkout", "route", "release"] * 3 + ["close"]


def test_a_route_that_raises_still_releases_the_connection():
    with TestClient(api.app, raise_server_exceptions=False) as client:
        response = client.get("/_boom")
        assert response.status_code == 500
    assert api.EVENTS == ["open", "checkout", "route", "release", "close"]


def test_an_http_error_from_the_route_keeps_its_status_and_still_releases():
    with TestClient(api.app) as client:
        response = client.get("/_missing")
        assert response.status_code == 404
        assert response.json() == {"detail": "no such row"}
        assert api.EVENTS == ["open", "checkout", "route", "release"]


def test_the_pool_is_in_lifespan_state_and_is_closed_at_shutdown():
    with TestClient(api.app) as client:
        assert client.get("/_probe").json() == {"pool": "FakePool"}
        assert client.get("/rows").status_code == 200
        pool = POOLS[0]
        assert pool.in_use == 0, "every connection should be back in the pool"
        assert not pool.closed
    assert pool.closed
