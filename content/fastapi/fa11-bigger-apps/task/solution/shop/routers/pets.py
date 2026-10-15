from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import require_key

router = APIRouter(
    prefix="/pets",
    tags=["pets"],
    dependencies=[Depends(require_key)],
    responses={404: {"description": "Pet not found"}},
)

PETS = {1: {"name": "Rex"}, 2: {"name": "Tom"}}


@router.get("/")
def list_pets() -> dict[int, dict[str, str]]:
    return PETS


@router.get("/{pet_id}")
def read_pet(pet_id: int) -> dict[str, str]:
    if pet_id not in PETS:
        raise HTTPException(status_code=404, detail="Pet not found")
    return PETS[pet_id]


@router.put("/{pet_id}", tags=["adoption"])
def adopt_pet(pet_id: int) -> dict[str, object]:
    if pet_id not in PETS:
        raise HTTPException(status_code=404, detail="Pet not found")
    return {"pet_id": pet_id, "adopted": True}
