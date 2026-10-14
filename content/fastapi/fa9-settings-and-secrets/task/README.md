# Task: settings that stay secret

Open `workspace/fa9-settings-and-secrets/config_app.py`. It has a small FastAPI app. The settings
class is empty, `get_settings()` builds a new object each time, and both routes return nothing
useful. Your job is to read the settings from environment variables, build them once, and keep the
key out of every response.

## 1. The `Settings` class

Give `Settings` three fields:

| Field | Type | Default |
| --- | --- | --- |
| `app_name` | `str` | none, so it is required |
| `max_items` | `int` | `10` |
| `api_key` | `str` | none, so it is required. This is the secret |

Add a `model_config` with `SettingsConfigDict(env_file=".env")`. You do not need to create that
file. The hidden tests run in an empty folder and set the variables themselves.

A `MAX_ITEMS` that is not a whole number must raise a `ValidationError` when the settings are
built. You get that for free from the `int` type.

## 2. Build it once

Put `@lru_cache` on `get_settings()`. Two calls must return the same object.

## 3. `GET /info`

Ask for the settings with a dependency: `settings: Annotated[Settings, Depends(get_settings)]`.
Return `{"app_name": ..., "max_items": ...}`. Do not return the key. Do not return the whole
settings object either, because it holds the key.

## 4. `GET /key-length`

Use the same dependency. Return `{"key_length": <the length of api_key>}`. The key itself must
never be in a response.

## Check your work

The hidden tests set `APP_NAME`, `MAX_ITEMS` and `API_KEY` with `monkeypatch`, and they never read a
real env file. They check the converted values, the `ValidationError` for a bad number, that two
calls to `get_settings()` give the same object, that `app.dependency_overrides` can replace
`get_settings`, and that the key text is not in any response body. If the override test fails,
check that both routes get the settings through `Depends(get_settings)` and not by calling
`Settings()` themselves.
