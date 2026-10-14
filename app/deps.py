from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends

from app.config import settings
from app.store import Store, open_store
from app.store_pg import open_pg_store


def open_store_from_settings() -> Store:
    """Postgres when DATABASE_URL is set, else the local SQLite file (the phase 1 default)."""
    if settings.database_url:
        return open_pg_store(settings.database_url)
    return open_store(settings.hintkata_db_path)


def get_store() -> Iterator[Store]:
    store = open_store_from_settings()
    try:
        yield store
    finally:
        store.close()


def get_user_id(store: Annotated[Store, Depends(get_store)]) -> int:
    return store.ensure_user("owner")
