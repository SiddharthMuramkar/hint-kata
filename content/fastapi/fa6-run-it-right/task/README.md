# Task: wire up a tiny project

Open the folder `workspace/fa6-run-it-right/`. It holds two files, `pyproject.toml` and `main.py`.
Together they are a tiny project that is not wired up yet. The `fastapi` command could not find
the app, the route is missing, and the FastAPI version has no limits. You will fix all three.

The hidden tests read your `pyproject.toml` the way the `fastapi` command does. They take the
entrypoint from `[tool.fastapi]`, import the app from it, and call the app with a test client.
They do not know the name of your app. They only know what your pyproject says.

## 1. Pin FastAPI

In `pyproject.toml`, the dependency is plain `"fastapi"`. Change it to ask for the `standard` extra
(`standard-no-fastapi-cloud-cli` also passes) and to stay inside the 0.143 minor. That means at
least 0.143.0 and below 0.144.0. The test reads your range, so any way of writing that range works.

## 2. Write the entrypoint

The `[tool.fastapi]` table has `entrypoint = "TODO"`. Replace the text with the import string of
the app in `main.py`. The format is `module:variable`.

The app in `main.py` is called `server`. You have two good choices. Rename the variable to `app`
and write `main:app`. Or keep `server` and write `main:server`. Either one passes. What matters
is that the two files agree.

## 3. Add the route

Add `GET /` to `main.py`. It returns `{"message": "Hello World"}`. The route must also show up in
`/openapi.json`, but that happens by itself when you declare it the normal way.

## Try it yourself (optional)

The hidden tests do not start a server. Once all three steps are done, you can see your app run.
Open a terminal in `workspace/fa6-run-it-right/` and run `uv run fastapi dev`. The start-up message
shows the import string it used. Then open `http://127.0.0.1:8000/docs`. Stop it with Ctrl+C.

## Check your work

If a test fails, read the message. It says which piece is wrong: the entrypoint text, the
object it points at, the `standard` extra, or the version range.
