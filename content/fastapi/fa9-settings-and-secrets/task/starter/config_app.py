from fastapi import FastAPI
from pydantic_settings import BaseSettings

app = FastAPI()


# TODO 1 (the settings class): give `Settings` these fields, read from environment variables:
#     app_name: str            (required)
#     max_items: int = 10      (optional, default 10)
#     api_key: str             (required, a secret)
#   Also add a `model_config` that points at a file called ".env":
#     model_config = SettingsConfigDict(env_file=".env")     (import SettingsConfigDict)
class Settings(BaseSettings):
    pass


# TODO 2 (build it once): make `get_settings()` return the same Settings object every time.
#   Put `@lru_cache` on it (from functools import lru_cache).
def get_settings() -> Settings:
    return Settings()


# TODO 3 (/info): ask FastAPI for the settings with a dependency, like this:
#     settings: Annotated[Settings, Depends(get_settings)]     (import Annotated and Depends)
#   Return {"app_name": ..., "max_items": ...}. Never return the key, and never return the
#   whole settings object (it holds the key).
@app.get("/info")
def info():
    return {}


# TODO 4 (/key-length): use the same dependency. Return {"key_length": <length of api_key>}.
#   The key itself must never be in the response.
@app.get("/key-length")
def key_length():
    return {}
