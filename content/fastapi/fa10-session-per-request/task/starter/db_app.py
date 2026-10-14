import os  # noqa: F401  (you will use it in get_conn)
import sqlite3
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel

DB_PATH = "notes.db"  # the default file; the env var NOTES_DB_PATH wins when it is set
SCHEMA = "CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY, body TEXT NOT NULL)"

app = FastAPI()


class NoteIn(BaseModel):
    body: str


# TODO 1 (one connection per request): write the dependency.
#   - Pick the path: os.environ.get("NOTES_DB_PATH", DB_PATH). Read it each time get_conn runs,
#     not when the module is imported.
#   - Open a NEW connection with sqlite3.connect(...). Pass check_same_thread=False.
#   - Run SCHEMA on it so the table exists.
#   - yield the connection.
#   - If the route returned normally: commit.
#   - If anything was raised: roll back, then raise it again.
#   - Always close the connection (finally).
def get_conn() -> Iterator[sqlite3.Connection]:
    raise NotImplementedError("write get_conn")
    yield  # keeps this a generator function; remove it when you write the real code


# TODO 2 (when does the exit code run?): by default the code after `yield` runs AFTER the
#   response has gone out. Change the Depends below so it runs right after the route
#   function returns, BEFORE the response is sent. Read the lesson section on commit timing.
Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


# TODO 3: insert the note and return {"id": <the new row id>}. Do not commit here.
#   A sqlite3 cursor has the new id in `.lastrowid`.
@app.post("/notes")
def add_note(note: NoteIn, conn: Conn) -> dict[str, int]:
    raise NotImplementedError("write add_note")


# TODO 4: insert the note, then raise an exception (any exception). The insert must NOT be
#   saved. Do not roll back here; the dependency does that.
@app.post("/notes/fail")
def add_note_then_fail(note: NoteIn, conn: Conn) -> dict[str, int]:
    raise NotImplementedError("write add_note_then_fail")
