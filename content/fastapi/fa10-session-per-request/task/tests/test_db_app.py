import asyncio
import inspect
import json
import sqlite3

import db_app  # the learner's db_app.py, on PYTHONPATH
import pytest
from fastapi.testclient import TestClient

REAL_CONNECT = sqlite3.connect  # saved before any test patches it


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """A temp database file. Both the env var and the module constant point at it, so the
    test works whichever one your get_conn reads."""
    path = str(tmp_path / "notes.db")
    monkeypatch.setenv("NOTES_DB_PATH", path)
    monkeypatch.setattr(db_app, "DB_PATH", path)
    return path


@pytest.fixture
def opened(monkeypatch):
    """Record every connection that sqlite3.connect opens, and the SQL each one runs."""
    conns: list[sqlite3.Connection] = []
    statements: list[list[str]] = []

    def spy(*args, **kwargs):
        conn = REAL_CONNECT(*args, **kwargs)
        sql: list[str] = []
        conn.set_trace_callback(sql.append)
        conns.append(conn)
        statements.append(sql)
        return conn

    monkeypatch.setattr(sqlite3, "connect", spy)
    return conns, statements


@pytest.fixture
def client(db_path):
    # raise_server_exceptions=False: an error inside a route becomes a 500, as it would on a
    # real server, instead of being re-raised into the test.
    return TestClient(db_app.app, raise_server_exceptions=False)


def saved_rows(path: str) -> list[tuple]:
    conn = REAL_CONNECT(path)
    try:
        return conn.execute("SELECT id, body FROM notes ORDER BY id").fetchall()
    finally:
        conn.close()


def is_closed(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError:
        return True
    return False


def test_get_conn_is_a_generator_dependency():
    assert inspect.isgeneratorfunction(db_app.get_conn), "get_conn must use yield"


def test_post_notes_saves_a_row_and_returns_its_id(client, db_path):
    response = client.post("/notes", json={"body": "hello"})
    assert response.status_code == 200
    assert saved_rows(db_path) == [(1, "hello")]
    assert response.json() == {"id": 1}


def test_ids_keep_counting_across_requests(client, db_path):
    ids = [client.post("/notes", json={"body": text}).json()["id"] for text in ("a", "b")]
    assert ids == [1, 2]
    assert saved_rows(db_path) == [(1, "a"), (2, "b")]


def test_failing_route_rolls_back(client, db_path, opened):
    _, statements = opened
    client.post("/notes", json={"body": "kept"})
    response = client.post("/notes/fail", json={"body": "lost"})
    assert response.status_code >= 400
    inserts = [s for s in statements[1] if s.lstrip().upper().startswith("INSERT")]
    assert inserts, "the failing route should INSERT before it raises"
    assert saved_rows(db_path) == [(1, "kept")], "the insert from the failing route was saved"


def test_connection_is_closed_after_each_request(client, db_path, opened):
    conns, _ = opened
    assert client.post("/notes", json={"body": "one"}).status_code == 200
    assert len(conns) == 1, "open exactly one connection per request"
    assert is_closed(conns[0]), "the connection was left open after a good request"
    assert client.post("/notes/fail", json={"body": "two"}).status_code >= 400
    assert len(conns) == 2
    assert is_closed(conns[1]), "the connection was left open after a failed request"
    assert client.post("/notes", json={"body": "three"}).status_code == 200
    assert [r[1] for r in saved_rows(db_path)] == ["one", "three"]


def test_each_request_gets_its_own_connection(client, db_path, opened):
    conns, _ = opened
    client.post("/notes", json={"body": "a"})
    client.post("/notes", json={"body": "b"})
    assert len(conns) == 2
    assert conns[0] is not conns[1]


def test_commit_happens_before_the_response_is_sent(db_path):
    """Call the app directly and look at the file at the moment the response starts."""
    seen: list[int] = []
    body = json.dumps({"body": "early"}).encode()
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message):
        if message["type"] == "http.response.start":
            seen.append(len(saved_rows(db_path)))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/notes",
        "raw_path": b"/notes",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json"), (b"content-length", b"%d" % len(body))],
        "server": ("testserver", 80),
        "client": ("testclient", 5000),
    }
    asyncio.run(db_app.app(scope, receive, send))
    assert seen == [1], "the row was not saved yet when the response started (see TODO 2)"
