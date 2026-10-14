# Task: a notes API with one connection per request

Open `workspace/fa10-session-per-request/db_app.py`. It is a tiny notes API on top of the standard
library's `sqlite3`. There is no SQLModel here, and the SQL is already short. Your job is the
part the lesson is about: **who opens the connection, who commits, and who closes it.** The
route functions must do none of those three things.

## 1. The `get_conn` dependency

Write `get_conn` as a dependency with `yield`.

- Take the database path from the environment variable `NOTES_DB_PATH` if it is set. Otherwise
  use the constant `DB_PATH`. Read it each time `get_conn` runs, not when the module loads.
- Open a **new** connection with `sqlite3.connect(...)` for every request. Pass
  `check_same_thread=False`.
- Run `SCHEMA` on it, so the table exists.
- `yield` the connection.
- If the route returned normally, commit.
- If anything was raised, roll back and raise it again, so FastAPI still answers with an error.
- Always close the connection, whatever happened.

Call it as `sqlite3.connect(...)` after `import sqlite3`. The tests watch that call.

## 2. When the exit code runs

By default, the code after `yield` runs after the response has gone out. A commit that fails
then cannot change what the client was told. Change the `Depends(...)` in the `Conn` alias so
the code after `yield` runs as soon as the route function returns, before the response is sent.

## 3. `POST /notes`

Send `{"body": "some text"}`. Insert a row into `notes`, and return `{"id": <the new id>}`. Do not
commit in the route.

## 4. `POST /notes/fail`

Same body. Insert the row, then raise an exception. Any exception will do. After this request
there must be **no** new row in the database, and you must not roll back in the route. That is
the dependency's job.

## Check your work

The hidden tests use a temporary database file. They check that

- a row exists after `POST /notes`, and the returned id is its id,
- no row exists after `POST /notes/fail`,
- every request opens exactly one connection, and the connection is closed afterwards (also
  after a failure),
- two requests in a row get two different connections,
- the row is already saved at the moment the response starts.

If a test fails, ask yourself: did the route do work that belongs to the dependency, or did the
dependency run at the wrong time?
