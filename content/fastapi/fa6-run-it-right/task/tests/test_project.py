"""Hidden checks for FA6. They read pyproject.toml the way the fastapi command does."""

import importlib
import re
import tomllib
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

PYPROJECT = Path("pyproject.toml")  # the checker runs with the workspace as the working directory
PIN = ">=0.143.0,<0.144.0"


def read_pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def load_app() -> FastAPI:
    """Import the app by the entrypoint in pyproject.toml, like `fastapi dev` does."""
    entrypoint = read_pyproject().get("tool", {}).get("fastapi", {}).get("entrypoint")
    assert isinstance(entrypoint, str) and re.fullmatch(
        r"[A-Za-z_][\w.]*:[A-Za-z_]\w*", entrypoint
    ), f"[tool.fastapi] entrypoint must look like 'module:variable', not {entrypoint!r}"
    module_name, _, variable = entrypoint.partition(":")
    module = importlib.import_module(module_name)
    app = getattr(module, variable, None)
    assert isinstance(app, FastAPI), (
        f"entrypoint {entrypoint!r}: module {module_name!r} has no FastAPI object "
        f"called {variable!r}"
    )
    return app


def fastapi_dependency() -> str:
    deps = read_pyproject().get("project", {}).get("dependencies", [])
    found = [d.replace(" ", "") for d in deps if re.match(r"fastapi(?![\w.-])", d.strip())]
    assert len(found) == 1, "[project] dependencies needs exactly one fastapi line"
    return found[0]


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(load_app())


def test_entrypoint_in_pyproject_imports_a_fastapi_app():
    load_app()


def test_root_route_answers(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_openapi_json_lists_the_root_route(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    body = response.json()
    assert body["openapi"].startswith("3.")
    assert "get" in body["paths"]["/"]


def test_fastapi_dependency_asks_for_the_standard_extra():
    dep = fastapi_dependency()
    assert dep.startswith("fastapi[standard]"), f"the fastapi command needs the extra: {dep!r}"


def test_fastapi_is_pinned_to_the_0_143_minor():
    dep = re.sub(r"\[.*?\]", "", fastapi_dependency())
    assert dep == f"fastapi{PIN}", f"expected fastapi{PIN}, found {dep!r}"
