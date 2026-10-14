from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:  # runs the lifespan (a no-op without a logfire token)
        yield c


def test_home_page_and_assets(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Hint Kata is not affiliated with GitHub, FastAPI or Pydantic." in r.text
    assert client.get("/static/css/app.css").status_code == 200


def test_licenses_page(client: TestClient) -> None:
    r = client.get("/licenses")
    assert r.status_code == 200
    assert "CC BY 4.0" in r.text


def test_healthz(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"ok": True}
