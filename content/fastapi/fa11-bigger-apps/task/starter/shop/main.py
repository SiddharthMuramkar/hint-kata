from fastapi import Depends, FastAPI, HTTPException

from shop.dependencies import require_key

# TODO 1 (routers): this flat app repeats the path start, the tag and the key check on every
#   route. Move the pet routes to shop/routers/pets.py and the owner routes to
#   shop/routers/owners.py. Each file makes `router = APIRouter(...)`. Create
#   shop/routers/__init__.py too. Then include both routers below.
# TODO 2 (admin): include the shared router `shop.internal.admin.router` with
#   prefix="/admin", tags=["admin"] and the key check. Do not edit admin.py.
# TODO 3 (tag metadata): pass `openapi_tags` to FastAPI() so the docs list the tags in this
#   order, each with a description: pets, owners, admin.

app = FastAPI()

PETS = {1: {"name": "Rex"}, 2: {"name": "Tom"}}
OWNERS = {1: {"name": "Ana"}}


@app.get("/")
def root() -> dict[str, str]:
    return {"shop": "open"}


@app.get("/pets/", tags=["pets"], dependencies=[Depends(require_key)])
def list_pets() -> dict[int, dict[str, str]]:
    return PETS


@app.get(
    "/pets/{pet_id}",
    tags=["pets"],
    dependencies=[Depends(require_key)],
    responses={404: {"description": "Pet not found"}},
)
def read_pet(pet_id: int) -> dict[str, str]:
    if pet_id not in PETS:
        raise HTTPException(status_code=404, detail="Pet not found")
    return PETS[pet_id]


@app.put(
    "/pets/{pet_id}",
    tags=["pets", "adoption"],
    dependencies=[Depends(require_key)],
    responses={404: {"description": "Pet not found"}},
)
def adopt_pet(pet_id: int) -> dict[str, object]:
    if pet_id not in PETS:
        raise HTTPException(status_code=404, detail="Pet not found")
    return {"pet_id": pet_id, "adopted": True}


@app.get("/owners/", tags=["owners"])
def list_owners() -> dict[int, dict[str, str]]:
    return OWNERS


@app.get("/owners/{owner_id}", tags=["owners"])
def read_owner(owner_id: int) -> dict[str, str]:
    if owner_id not in OWNERS:
        raise HTTPException(status_code=404, detail="Owner not found")
    return OWNERS[owner_id]
