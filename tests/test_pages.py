from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_home_page_and_assets() -> None:
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Hint Kata is not affiliated with GitHub, FastAPI or Pydantic." in r.text
    assert client.get("/static/css/app.css").status_code == 200


def test_licenses_page() -> None:
    r = client.get("/licenses")
    assert r.status_code == 200
    assert "CC BY 4.0" in r.text


def test_healthz() -> None:
    assert client.get("/healthz").json() == {"ok": True}
