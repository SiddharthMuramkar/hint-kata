from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends

from app.config import settings
from app.store import Store, open_store


def get_store() -> Iterator[Store]:
    store = open_store(settings.hintkata_db_path)
    try:
        yield store
    finally:
        store.close()


def get_user_id(store: Annotated[Store, Depends(get_store)]) -> int:
    return store.ensure_user("owner")
