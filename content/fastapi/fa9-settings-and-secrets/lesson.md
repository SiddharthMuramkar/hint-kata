---
id: fa9-settings-and-secrets
track: fastapi
title: "Settings and secrets with pydantic-settings"
minutes: 25
pins:
  fastapi: "0.143.0"
  pydantic-settings: "2.16.0"
sources:
  - fastapi-environment-variables
  - fastapi-advanced-settings
---

Every app has values that are not code. A database address. A model name. A limit. An API key. They change from one place to another: your laptop, a test run, a server. Some of them are secret.

One sentence is the whole mental model: **declare your settings as a typed class, let `pydantic-settings` fill it from outside your code, check the values when you build it, hand it to your routes through one cached dependency, and never show the secret ones.**

The rest of the lesson goes through that sentence in order. Environment variables first. Then the `Settings` class and what happens when a value is bad. Then the env file, the cached dependency, tests, and secrets. The last section reads this site's own settings.

This lesson builds on dependencies (FA1), testing (FA2) and lifespan (FA8). Overrides and lifespan come back here.

## Environment variables

An environment variable is a named piece of text that the operating system hands to a program when the program starts. Each program gets its own copy.

Python reads them from `os.environ`, which works like a dictionary.

```python
import os

os.environ["APP_NAME"]  # KeyError if it is not set
os.environ.get("APP_NAME")  # None if it is not set
os.environ.get("APP_NAME", "x")  # "x" if it is not set
```

Two facts matter.

- Every value is a `str`. `MAX_ITEMS=5` gives you the text `"5"`, not the number 5. Nothing converts it for you.
- You cannot put a number in. `os.environ["N"] = 5` raises `TypeError: str expected, not int`. Write `"5"`.

Here is how to set one, in the terminal in VS Code on a Mac (zsh or bash).

- **One-off.** Put the assignments before the command: `APP_NAME=Demo MAX_ITEMS=3 uv run fastapi run main.py`. Only that command sees them. When we ran a Python one-liner this way it printed the value, and the next command in the same terminal printed `None`.
- **For the whole terminal.** Run `export APP_NAME=Demo`. Every command you start from that terminal now sees it. `unset APP_NAME` removes it. A new terminal tab does not have it. We ran this too.

A program gets a copy. If Python changes `os.environ` for itself, your terminal still has the old value.

On Windows PowerShell the FastAPI page uses the form `$Env:NAME = "value"`. We ran only the Mac commands.

Why not write the values in your code?

- **Different places need different values.** The same code runs on your laptop, in a test and on a server. A hard-coded value means editing code to move it.
- **Secrets end up in git.** A key in a Python file is in every commit after that. This repo is public. A deleted key is still in the history.
- **Changing a number should not mean changing code.** A limit is a setting, not logic.

More: [Environment Variables](https://fastapi.tiangolo.com/environment-variables/) and [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/).

## A Settings class with types and defaults

Because every environment variable is text, someone has to convert and check it. `pydantic-settings` does that. It is a separate package from Pydantic, pinned in this repo at 2.16.0. Its `BaseSettings` is a Pydantic model that fills its fields from environment variables.

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str
    max_items: int = 10
    api_key: str
```

How it behaves, as we ran it.

- The field `max_items` is filled from the variable `MAX_ITEMS`. Names are not case sensitive by default, so a lower-case `max_items` variable is read too.
- A field with no default is **required**. `app_name` and `api_key` here. A field with a default is optional. `max_items` is `10` when `MAX_ITEMS` is not set.
- The text is converted to the type you wrote. With `MAX_ITEMS=25`, `settings.max_items` is the `int` `25`.
- A `bool` field accepts words such as `true`, `1`, `yes` and `off`. Text such as `maybe` is an error.
- A list or other complex value must be written as JSON text, like `TAGS='["a","b"]'`. The text `a,b` fails too, but with a `SettingsError` from `pydantic_settings.exceptions`. It is raised while the value is read, before Pydantic checks anything, and it is not a `ValidationError`.
- Values you pass in code win over the environment. `Settings(app_name="x")` uses `"x"`.
- All the Pydantic tools work. `max_items: int = Field(default=10, ge=1)` rejects `MAX_ITEMS=0`, with the error type `greater_than_equal`, the same way as in FA3.

The FastAPI page shows the package installed with `uv add pydantic-settings`. This repo already has it.

More: [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/), the part called "Create the Settings object". The full list of options is in the [pydantic-settings documentation](https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/).

## When a value is bad

The check happens when you build the object, `Settings()`. If a value is the wrong type or breaks a rule, you get a `ValidationError` and no object. It is the same error class you know from FA3, and you import it with `from pydantic import ValidationError`.

Missing both required values:

```text
2 validation errors for Settings
app_name
  Field required [type=missing, input_value={}, input_type=dict]
api_key
  Field required [type=missing, input_value={}, input_type=dict]
```

A bad number, with `MAX_ITEMS=lots`:

```text
1 validation error for Settings
max_items
  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, input_value='lots', input_type=str]
```

Each error also has a link line, which we left out. In code, `error.errors()` gives a list with one dictionary per problem. The keys are `type`, `loc`, `msg`, `input` and `url`, and sometimes `ctx`. This is the same shape as the 422 body in FA5, with one difference. `loc` is a tuple of just the field name, like `('max_items',)`. There is no `path` or `query` in front, because no request is involved.

Look at `input_value`. The error prints the text it could not use. For `lots` that is harmless. If a secret fails a rule, the secret is printed too. We saw this with a key that was too short: the key appeared in the message. Keep the rules on secrets simple, and do not paste startup errors into a public place.

**When does it fail?** That depends on when you build the object.

- With a plain `settings = Settings()` at the top of a module, it fails when the module is imported. The program never starts. That is the good case.
- With a lazy `get_settings()`, which the later sections use, the server **starts fine**. The first request that needs the settings gets a 500 `Internal Server Error`, and the `ValidationError` is in the server log. The next request fails the same way. We ran this with `fastapi run` and no variables set: the server came up and `/info` answered 500.

To make the lazy version fail at start, build the settings once in a lifespan function, as in FA8.

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()  # raises ValidationError here, and the app does not start
    yield


app = FastAPI(lifespan=lifespan)
```

We ran this with `MAX_ITEMS=lots`. Starting the app raised the `ValidationError`. With a good value it started.

More: [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/), the part called "Types and validation".

## The env file and empty values

Typing ten `export` lines is tedious. An env file holds them instead: one `NAME=value` per line. You name it in the config.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    app_name: str
    max_items: int = 10
    api_key: str
```

The file is conventionally called `.env`, and people call it a "dotenv" file. The FastAPI page says to install `python-dotenv` for this. In this repo it is already installed, because `pydantic-settings` 2.16.0 lists it as a dependency in `uv.lock`.

What we saw when we ran it.

- **A real variable beats the file.** With `APP_NAME=demo` in the environment and `APP_NAME=fromfile` in the file, the value is `demo`. The order, strongest first: values passed in code, then environment variables, then the file, then the field default.
- **A missing file is fine.** No error. The fields just have to come from somewhere else.
- **The path is relative to where you start the program.** `".env"` means the `.env` in the current folder, not next to your Python file. We built the settings from a sub-folder and the values were missing. Start your server from the project root.
- **Unknown names in the file are an error by default.** `BaseSettings` defaults to `extra="forbid"`, so a line `OTHER_THING=1` raises `extra_forbidden`. Variables in the real environment do not trigger this. Add `extra="ignore"` to the config to allow other lines.

**Empty values.** A copied example file has lines like `MAX_ITEMS=`. That is a variable set to the empty string. By default, an empty string is a value. For an `int` field it fails with `int_parsing`, and for a `str` field it replaces your default with `""`. Set `env_ignore_empty=True` and an empty value counts as "not set". The default is used. A required field with an empty value still fails with `missing`.

```python
model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)
```

**Switching the file off.** `Settings(_env_file=None)` builds the object without reading any file. Tests use this a lot. The next two sections show where.

More: [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/), the part called "Reading a .env file".

## One cached settings dependency

Where do the routes get the settings? A global `settings = Settings()` works, but a test cannot swap it easily. FastAPI's answer is a dependency, as in FA1.

```python
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]


@app.get("/info")
def info(settings: SettingsDep):
    return {"app_name": settings.app_name, "max_items": settings.max_items}
```

`@lru_cache` remembers the result of a call. The function has no arguments, so the first call builds the object and every later call returns **the same object**. We checked: `get_settings() is get_settings()` is `True`, and the body ran once.

Why cache? Each `Settings()` reads the environment and the file again. We saw that a new object picks up an edited file. Doing that on every request is wasted work, and the values should not change under a running server.

The same fact has a cost. After the first call, a change to the environment is not seen. In our run the cached object kept `max_items` at `25` after we set `MAX_ITEMS=99`. `get_settings.cache_clear()` empties the cache, and the next call builds a new object. Outside tests you rarely need it. To pick up a changed file, restart the server.

Notice what `info` returns: two fields it picked by hand. It does not return `settings`. The reason is in the secrets section, two sections down.

More: [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/), the parts called "Settings in a dependency" and "Creating the Settings only once with lru_cache".

## Overriding settings in tests

There are two things to test: the routes with chosen settings, and `get_settings()` itself. Neither should read your real env file.

**Routes with chosen settings.** Replace the dependency, as in FA1 and FA2.

```python
from fastapi.testclient import TestClient


def fake_settings() -> Settings:
    return Settings(app_name="Test", max_items=3, api_key="test-key", _env_file=None)


def test_info():
    app.dependency_overrides[get_settings] = fake_settings
    try:
        response = TestClient(app).get("/info")
    finally:
        app.dependency_overrides.clear()
    assert response.json() == {"app_name": "Test", "max_items": 3}
```

Points we checked by running.

- The key in `dependency_overrides` is the `get_settings` function itself, the one you gave to `Depends`. It works with the `@lru_cache` wrapper.
- The real `get_settings` never runs. We set `MAX_ITEMS=lots` in the environment and the override still answered 200. The cache showed no calls.
- `_env_file=None` keeps your local file out of the test. Without it, any field you did not pass is filled from the environment and the file. Pass every field you need.
- Clear the overrides when you are done. One test's override leaks into the next one otherwise.

**The real `get_settings()`.** Set the environment with `monkeypatch`, and clear the cache so an earlier test's object is gone.

```python
def test_get_settings_reads_the_environment(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # an empty folder: no env file here
    monkeypatch.setenv("APP_NAME", "Demo")
    monkeypatch.setenv("API_KEY", "test-key")
    monkeypatch.setenv("MAX_ITEMS", "25")
    get_settings.cache_clear()
    try:
        assert get_settings().max_items == 25
        assert get_settings() is get_settings()
    finally:
        get_settings.cache_clear()
```

`monkeypatch.chdir(tmp_path)` works because `".env"` is relative to the current folder. In an empty folder there is no file to read. `monkeypatch.setenv` puts the variable back to its old value after the test. The `cache_clear()` calls matter: without the first one you may get a stale object, and without the last one the next test inherits yours.

A bad value is tested with `pytest.raises(ValidationError)`. Check `loc` and `type` on the error, not the message text, as in FA5.

More: [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/), the part called "Settings and testing".

## Keeping secrets out of git and logs

Three jobs: keep the file out of git, keep values out of output, and treat a leak as a leak.

**Keep the file out of git.** On 2026-10-15 this repo's `.gitignore` had these lines, in this order.

```text
.env
.env.*
!.env.example
```

The first two ignore the real file and variants like `.env.local`. The third makes an exception for the example file. On 2026-10-15, `git check-ignore -v` confirmed that `.env` and `.env.local` are ignored and `.env.example` is not.

**Commit a names-only example.** `.env.example` lists every variable with an empty value and a comment. A new person copies it to `.env` and fills in the values. It has no secrets, so it is safe in a public repo. With `env_ignore_empty=True`, a copy of it with nothing filled in still loads, as the site section shows.

**Ignoring comes too late for a committed file.** We made a throwaway repo, committed a file, then added it to `.gitignore`. Git still tracked the file and showed later edits. `git rm --cached` stops tracking it from the next commit, but `git log` still found the old commit. So if a real key was ever committed, treat it as leaked. Make a new key at the provider and revoke the old one.

**Keep values out of output.** A `Settings` object with a plain `str` prints its secrets. We ran this.

- `print(settings)` shows `api_key='fake-key-123'`.
- A route that returns the settings object sends `{"api_key":"fake-key-123"}` to the client.

Use `SecretStr` for secret fields.

```python
from pydantic import SecretStr


class Settings(BaseSettings):
    api_key: SecretStr
```

Now `print(settings)` shows `api_key=SecretStr('**********')`, and a route that returns the object sends `"**********"`. To use the real text, call `settings.api_key.get_secret_value()` at the one place that needs it, such as when you build the client for another service.

Two cautions from our runs. `len()` of a `SecretStr` gives the length of the secret. And the `ValidationError` printed the value of a secret that failed a rule.

**Mask in logs.** Log that a secret exists, not what it is: `set` or `not set`. A first-two-characters hint still leaks part of a short key. Do not put settings objects, request headers or full error messages from the settings into logs without looking at them first.

The hands-on task asks for a route that returns only the key's length. That is a small leak, enough for an exercise. A real route would return nothing about the key at all.

## How this site does it

This site is a worked example. We read these files and ran these checks on 2026-10-15; the values may have changed since. The code is in `app/config.py`, the names are in `.env.example`, and the rules are in `CLAUDE.md` and `docs/RESUME.md`.

**One `Settings` class, built once.** `app/config.py` has a `Settings(BaseSettings)` and, under it, `settings = Settings()`. That object is created when `app.config` is first imported, and other modules import it. The site does not use the `lru_cache` dependency, because agents and scripts need settings outside any request. Tests use `monkeypatch.setattr(settings, ...)` or build a fresh `Settings(_env_file=None)`.

Because it is built at import, a bad value stops the program at the start. We ran `import app.config` with `EMBED_DIMS=abc` and got a `ValidationError` with `int_parsing`.

**The config line.** `env_file=".env"`, `extra="ignore"` and `env_ignore_empty=True`. We built the site's `Settings` from a copy of `.env.example` with every value empty. It loaded, and the defaults were in place: `tutor_model` was the default model and `embed_dims` was the `int` 1536. Without `env_ignore_empty`, the empty `EMBED_DIMS=` line would have failed.

**Every field has a default.** The site starts with an empty env file. The key is `openrouter_api_key: str = ""`, and the code checks `if settings.openrouter_api_key` to see whether it is set. This is a plain `str`, not a `SecretStr`. The site protects it by never printing or returning it, and by keeping the file out of git.

**Model names.** `tutor_model` is `openrouter:anthropic/claude-haiku-5.5`. `grader_model`, `author_model` and `judge_model` are `openrouter:anthropic/claude-sonnet-5.5`. `embed_model` is `openrouter:openai/text-embedding-3-small`, with `embed_dims` of `1536`. A comment says `embed_dims` must equal the size of the database column. Each can be changed with a variable such as `TUTOR_MODEL`.

**Caps.** `rag_k`, how many docs chunks the tutor gets, defaults to `6`. A `field_validator` clamps it to the range 1 to 10. We ran `RAG_K=100` and got `10`, and `RAG_K=0` and got `1`. The other limits are not settings. `max_tokens` is written in the agent code: 1200 for the tutor and 1500 for the grader. The spend cap on the OpenRouter key is set in the OpenRouter dashboard, as the spec says.

**Who types the secrets.** `.env.example` marks `OPENROUTER_API_KEY`, `DATABASE_URL`, `DATABASE_URL_UNPOOLED` and `LOGFIRE_TOKEN` as secret. `CLAUDE.md` says secrets live only in the local env file and in GitHub secrets, that the owner types the values, and that Claude never reads, prints, edits or commits them. The file is denied to Claude by the project settings. `docs/RESUME.md` repeats it for the Neon and Vercel steps. The site follows the pattern from this lesson.

Sources (FastAPI 0.143.0, MIT licence, © 2018 Sebastián Ramírez; adapted and rewritten): [Settings and Environment Variables](https://fastapi.tiangolo.com/advanced/settings/), [Environment Variables](https://fastapi.tiangolo.com/environment-variables/). This site is not affiliated with FastAPI or Pydantic.
