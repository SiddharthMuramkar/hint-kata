from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic_settings import BaseSettings, SettingsConfigDict

app = FastAPI()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str
    max_items: int = 10
    api_key: str  # a secret: read it from the environment, never return it


@lru_cache  # no arguments, so the first call builds the object and every call returns it
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


@app.get("/info")
def info(settings: SettingsDep):
    # Pick the safe fields by hand. Returning `settings` would send the key too.
    return {"app_name": settings.app_name, "max_items": settings.max_items}


@app.get("/key-length")
def key_length(settings: SettingsDep):
    return {"key_length": len(settings.api_key)}
