import importlib

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from shop.main import app

client = TestClient(app)
spec = client.get("/openapi.json").json()
KEY = {"X-Key": "letmein"}


def router_of(module: str) -> APIRouter:
    try:
        mod = importlib.import_module(module)
    except ModuleNotFoundError as exc:
        pytest.fail(f"cannot import {module}: {exc}")
    assert isinstance(mod.router, APIRouter), f"{module}.router must be an APIRouter"
    return mod.router


def tags_of(path: str, method: str) -> list[str]:
    return spec["paths"][path][method].get("tags", [])


def test_the_two_routers_exist_and_carry_the_shared_settings():
    pets = router_of("shop.routers.pets")
    assert pets.prefix == "/pets"
    assert pets.tags == ["pets"]
    assert len(pets.dependencies) == 1, "put the key check on the router, once"
    owners = router_of("shop.routers.owners")
    assert owners.prefix == "/owners"
    assert owners.tags == ["owners"]
    assert owners.dependencies == []


def test_admin_router_file_is_untouched():
    admin = router_of("shop.internal.admin")
    assert (admin.prefix, admin.tags, admin.dependencies) == ("", [], [])


def test_paths():
    assert set(spec["paths"]) == {
        "/",
        "/pets/",
        "/pets/{pet_id}",
        "/owners/",
        "/owners/{owner_id}",
        "/admin/",
    }


def test_tags_on_each_operation():
    assert tags_of("/", "get") == []
    assert tags_of("/pets/", "get") == ["pets"]
    assert tags_of("/pets/{pet_id}", "get") == ["pets"]
    assert tags_of("/pets/{pet_id}", "put") == ["pets", "adoption"]
    assert tags_of("/owners/", "get") == ["owners"]
    assert tags_of("/owners/{owner_id}", "get") == ["owners"]
    assert tags_of("/admin/", "post") == ["admin"]


def test_tag_metadata_lists_the_tags_in_order_with_descriptions():
    listed = spec.get("tags", [])
    assert [t["name"] for t in listed] == ["pets", "owners", "admin"]
    assert all(t.get("description") for t in listed)


def test_the_404_response_is_documented_on_every_pet_operation():
    for method, path in (("get", "/pets/"), ("get", "/pets/{pet_id}"), ("put", "/pets/{pet_id}")):
        assert "404" in spec["paths"][path][method]["responses"], (method, path)
    assert "404" not in spec["paths"]["/owners/"]["get"]["responses"]


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/pets/"), ("get", "/pets/1"), ("put", "/pets/1"), ("post", "/admin/")],
)
def test_key_check_applies_to_pets_and_admin(method, path):
    assert client.request(method, path).status_code == 422  # header missing
    assert client.request(method, path, headers={"X-Key": "nope"}).status_code == 401
    assert client.request(method, path, headers=KEY).status_code == 200


def test_key_header_shows_up_in_the_docs_for_pets_and_admin_only():
    def header_names(path: str, method: str) -> list[str]:
        params = spec["paths"][path][method].get("parameters", [])
        return [p["name"] for p in params if p["in"] == "header"]

    assert header_names("/pets/", "get") == ["x-key"]
    assert header_names("/admin/", "post") == ["x-key"]
    assert header_names("/owners/", "get") == []
    assert header_names("/", "get") == []


def test_owners_and_root_need_no_key():
    assert client.get("/").json() == {"shop": "open"}
    assert client.get("/owners/").status_code == 200
    assert client.get("/owners/1").json() == {"name": "Ana"}
    assert client.get("/owners/9").status_code == 404


def test_behaviour_of_the_pet_routes():
    assert client.get("/pets/1", headers=KEY).json() == {"name": "Rex"}
    assert client.get("/pets/9", headers=KEY).status_code == 404
    assert client.put("/pets/2", headers=KEY).json() == {"pet_id": 2, "adopted": True}
    assert client.post("/admin/", headers=KEY).json() == {"message": "shop reset"}
