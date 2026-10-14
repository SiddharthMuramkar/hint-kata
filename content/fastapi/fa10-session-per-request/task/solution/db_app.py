import os
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


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(os.environ.get("NOTES_DB_PATH", DB_PATH), check_same_thread=False)
    try:
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


# scope="function": the exit code (commit or rollback, then close) runs right after the route
# function returns, before the response is sent.
Conn = Annotated[sqlite3.Connection, Depends(get_conn, scope="function")]


@app.post("/notes")
def add_note(note: NoteIn, conn: Conn) -> dict[str, int]:
    cur = conn.execute("INSERT INTO notes (body) VALUES (?)", (note.body,))
    return {"id": cur.lastrowid or 0}


@app.post("/notes/fail")
def add_note_then_fail(note: NoteIn, conn: Conn) -> dict[str, int]:
    conn.execute("INSERT INTO notes (body) VALUES (?)", (note.body,))
    raise RuntimeError("something went wrong after the insert")
