Lesson FA9 teaches how a FastAPI app gets its settings and keeps its secrets. You declare the settings as a typed class, let `pydantic-settings` fill it from outside your code, and hand it to your routes through one cached dependency. The reading has eight short sections, from environment variables and a `BaseSettings` class to the env file, `get_settings()` with `@lru_cache`, tests with `app.dependency_overrides`, keeping secrets out of version control and logs, and how this site does it. It also has 2 warm-up predictions, a 6-item quiz and 2 think-deeper questions.

It matters because settings are where a real app meets the outside world, and a leaked key is hard to undo. The hands-on task is `config_app.py`: you write a `Settings` class, cache `get_settings()`, and add `/info` and `/key-length` so the key never appears in a response. 13 hidden tests use `monkeypatch` in an empty folder, so no real env file is read. The starter fails and the solution passes. The lesson pins FastAPI 0.143.0 and pydantic-settings 2.16.0, and every code block and runtime claim was run in a scratch folder with fake values first.

Read `content/fastapi/fa9-settings-and-secrets/lesson.md` first, then `task/README.md`.

One lesson learned: a cached `get_settings()` does not fail at start. We ran `fastapi run` with no variables set, and the server came up fine. The first request got a 500, and so did the next one, because `lru_cache` does not store a call that raised. A bare `Settings()` at module level fails at import, which is why this site's own `settings` object stops the program at once on a bad value. If you want the lazy version to fail early, call `get_settings()` once in a lifespan function. We also saw that the `ValidationError` prints the text it could not use, so a bad secret can end up in a log. The FastAPI page says to install `python-dotenv`. In this repo it is already there, because `pydantic-settings` depends on it. A ten-line run showed all three, and the lesson says what we saw.

Closes #81

🤖 Generated with [Claude Code](https://claude.com/claude-code)
