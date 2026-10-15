from fastapi import Depends, FastAPI

from .dependencies import require_key
from .internal import admin
from .routers import owners, pets

tags_metadata = [
    {"name": "pets", "description": "Look at the pets and adopt one."},
    {"name": "owners", "description": "The people who own pets."},
    {"name": "admin", "description": "Shop staff only."},
]

app = FastAPI(title="Pet shop", openapi_tags=tags_metadata)

app.include_router(pets.router)
app.include_router(owners.router)
app.include_router(
    admin.router,
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_key)],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"shop": "open"}
