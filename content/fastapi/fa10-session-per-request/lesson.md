---
id: fa10-session-per-request
track: fastapi
title: "Databases: a session per request"
minutes: 40
pins:
  fastapi: "0.143.0"
  psycopg: "3.3.6"
sources:
  - fastapi-tutorial-sql-databases
  - fastapi-tutorial-dependencies-with-yield
  - fastapi-advanced-events
  - fastapi-async
---

A web app that stores things needs a database connection. The question is who opens it, who saves the changes, and who closes it. If the answer is "every route, by hand", you will forget one of the three, sooner or later.

One sentence is the whole mental model: **each request gets its own connection, opened before your route runs and closed after it, and the route itself never opens, saves or closes anything.** FastAPI does this with a dependency that uses `yield`. You met that idea in lesson FA1. This lesson puts a database inside it.

We look at two real examples. First the official FastAPI tutorial, which uses SQLModel. Then this very site, which does the same job with the plain `sqlite3` module and `psycopg`. We read the SQLModel example. We ran everything else: the FastAPI behaviour and this site's own code. Where a claim comes from a run and not from a doc page, the lesson says so.

## What the official SQL tutorial teaches

The [SQL (Relational) Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/) page builds a small "heroes" API with [SQLModel](https://sqlmodel.tiangolo.com/). SQLModel is a library from the same author as FastAPI. It sits on top of SQLAlchemy and Pydantic, so one class is both a table and a Pydantic model. The page uses SQLite, because it is a single file and Python ships with it.

Four pieces matter for this lesson.

- **One engine for the whole app.** The engine is the object that holds the connections. You create it once.
- **`check_same_thread=False`.** The page passes this to SQLite's connect arguments. It gives the reason too: a single request may touch the connection from two threads, because a dependency and the route can run on different workers. By default SQLite refuses a connection that is used from a thread other than the one that made it.
- **A session per request.** A session keeps track of objects in memory and uses the engine to talk to the database. The page makes a dependency with `yield` that opens a `Session` in a `with` block, so each request gets a new one and it is closed afterwards. The routes ask for it with `Depends`, wrapped in an `Annotated` name.
- **Tables created at startup.** A function calls `SQLModel.metadata.create_all(engine)`, and a startup handler runs it when the app starts. The page adds that for production you would probably run a migration script before starting the app.

Here is the shape of the session part. This is our short version, not the page's code.

```python
def get_session():
    with Session(engine) as session:  # a new session for this request
        yield session  # the route uses it here; leaving the `with` closes it


SessionDep = Annotated[Session, Depends(get_session)]
```

The routes in the tutorial call `session.commit()` themselves. So in that example, the dependency opens and closes, and the route commits.

**A note about the startup handler.** The tutorial registers it with `@app.on_event("startup")`. We read the copy of the page for FastAPI 0.143.0 and looked for the words "deprecated" and "lifespan". The page has neither. But FastAPI 0.143.0 itself says otherwise. When we ran `@app.on_event("startup")`, Python printed a `DeprecationWarning`: "on_event is deprecated, use lifespan event handlers instead". And the [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) page has a section called "Alternative Events (deprecated)". It also says that once you give the app a `lifespan`, the old startup and shutdown handlers are no longer called. It is one style or the other, not both.

So the example still works, but it shows the old way. When you copy it, use a `lifespan` function instead. This site does: `app/main.py` has a `lifespan` that loads the lessons and opens a store for a moment to record the config.

More: [SQL (Relational) Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/), and [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/) for the `lifespan` function.

## What this site does instead

This site does not use SQLModel. It is not one of the pinned dependencies in `pyproject.toml`, and this lesson does not add it. The site uses the standard library's `sqlite3` on your Mac, and `psycopg` (version 3.3.6) for Postgres on Neon, which is the phase 2 database.

The reason for plain drivers is that the site must run on two databases with the same routes. The spec says the data sits behind a small store interface, so a Postgres store can drop in later. In code that interface is a `Protocol` in `app/store.py`.

```python
class Store(Protocol):
    # 19 methods in all; four of them:
    def ensure_user(self, name: str) -> int: ...
    def add_check(self, user_id: int, lesson_id: str, passed: bool, output: str) -> int: ...
    def last_check(self, user_id: int, lesson_id: str) -> dict[str, Any] | None: ...
    def close(self) -> None: ...
```

Two classes fill it in: `SqliteStore` in `app/store.py` and `PostgresStore` in `app/store_pg.py`. **All the SQL lives inside those two classes.** A route never sees a cursor or a query string. It calls `store.last_check(user_id, lesson_id)` and gets a dict back.

That has a cost and a gain.

- **Cost:** you write each query twice, once per database, and keep both in step. An ORM would write the SQL for you.
- **Gain:** the routes do not know or care which database is behind them. The store tests are written once. `tests/test_store_pg.py` imports them and runs them again against Postgres. Those tests need a real Postgres, so they are skipped when `TEST_DATABASE_URL` is not set.

Which store do you get? `app/deps.py` decides. If the setting `DATABASE_URL` is set, you get Postgres. Otherwise you get the SQLite file at `HINTKATA_DB_PATH`. The routes do not look at either setting.

More: the code itself. Read `app/store.py` and `app/store_pg.py` side by side. Nothing from the SQLModel page is used here.

## One connection per request

This is the whole dependency, from `app/deps.py`.

```python
def get_store() -> Iterator[Store]:
    store = open_store_from_settings()
    try:
        yield store
    finally:
        store.close()
```

It is the same shape as the official tutorial's session dependency, and the same shape as the `get_db` example on the [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/) page. Open, `yield`, close in `finally`. The `finally` is what makes it close on success and on an error alike.

A route asks for the store like this.

```python
@app.get("/api/progress")
def api_progress(
    request: Request,
    store: Annotated[Store, Depends(get_store)],
    user_id: Annotated[int, Depends(get_user_id)],
) -> dict[str, Any]: ...
```

Look closely. The route depends on `get_store`, and `get_user_id` depends on `get_store` too. Does that open two connections? We counted. We replaced the opener with a counting version and called `/api/progress` once. It opened **one** store, and that store was closed when the request ended. FastAPI reuses the result of a dependency inside one request. So "per request" means per request, not per place that asks.

**Why `check_same_thread=False`?** The site's `get_store` is a plain `def`, not `async def`. FastAPI runs plain `def` dependencies and routes in a [threadpool](https://fastapi.tiangolo.com/async/). The setup, the route and the exit code are separate calls into that pool, so they may run on different threads.

We tested it. We made a dependency that records its thread before the `yield`, in the route, and after the `yield`, and sent requests through two kinds of in-process client. With 20 requests sent one at a time, all three steps shared one thread every time. With 30 requests sent at once through `httpx.AsyncClient` and `asyncio.gather`, they shared one thread **zero** times out of 30. FastAPI's `TestClient` showed the opposite: sent from 30 threads, all 30 requests kept all three steps on one thread. So whether the problem shows up depends on the client and on the load. A quiet test can pass and real traffic can fail.

SQLite's default rule is the one the tutorial describes. We checked it:

```text
check_same_thread=True  -> ProgrammingError: SQLite objects created in a thread can only be used in that same thread. ...
check_same_thread=False -> ok
```

So the flag is safe here for one reason only: **each connection belongs to one request**. The flag does not make a connection safe to share between requests. If you put one connection in a module variable with the default flag, the route fails at once. We tried it, and the route answered 500. With the flag off it runs, and that is worse. We shared one connection between two "requests". The first inserted a row and did not finish. The second inserted a row and committed. The first then rolled back, and its row was already saved. One connection per request is the rule. The flag just lets that one request move between threads.

More: [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/), and [Concurrency and async / await](https://fastapi.tiangolo.com/async/) for what runs in the threadpool.

## Commit, rollback and when the exit code runs

Now the question of saving. The official tutorial commits inside the route. This site does neither of the obvious things. **It commits inside the store, one statement at a time.** Here is `_write` in `SqliteStore`.

```python
def _write(self, sql: str, params: tuple[Any, ...]) -> int:
    """Run one write, commit, return the row id of the insert."""
    try:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
    except BaseException:
        self.conn.rollback()
        raise
    return cur.lastrowid or 0
```

Every write method goes through it. It commits when the statement worked, and rolls back and raises again when it did not. `PostgresStore` has the same shape. The dependency `get_store` then has nothing left to do except close.

The reads follow the same pattern with a twist. `SqliteStore._all` calls `rollback()` after each `SELECT`. The code comment says why: it releases the read snapshot, and `sqlite3` opens a new transaction at once.

The result is simple to reason about, and it has one weak spot. **A route that makes two writes has two transactions.** We tried it. We called `add_attempt` once with good data and once with a bad `kind` that breaks a `CHECK` constraint. The second call raised `IntegrityError`, and the first row was still in the database. If a route needs both writes or neither, this design does not give that.

The other design is the one in this lesson's hands-on task: the dependency commits once, after the route returned.

```python
def get_conn():
    conn = sqlite3.connect(path, check_same_thread=False)
    try:
        yield conn
        conn.commit()  # the route returned normally
    except BaseException:
        conn.rollback()  # the route raised
        raise  # so FastAPI still sends an error
    finally:
        conn.close()
```

All the writes in one request then succeed or fail together. This works because an exception raised in the route is thrown into the dependency at its `yield`. We checked it with a `RuntimeError` and with an `HTTPException`: the dependency saw both, and no row was saved. The dependencies-with-yield page says the same and warns you to re-raise. If you catch the exception and do not raise it again, FastAPI never learns that anything went wrong.

A trap that looks tidy: put `conn.commit()` inside the `finally`. Then it runs on errors too. We tried it with a route that inserts and then raises. The client got a 500, and the half-finished row **was saved**.

### When does the code after `yield` run?

By default, **after the response has been sent.** The dependencies-with-yield page says this, and calls this default `scope="request"`. The same page describes `Depends(get_conn, scope="function")`. With it, the exit code runs right after the route function returns, before the response goes out.

We watched the order with a small ASGI call that looks at the database file at the moment the response starts.

| `scope` | Order of events | New rows another connection could see when the response started |
| --- | --- | --- |
| `"request"` (default) | response start, response body, then commit | 0 |
| `"function"` | commit, then response start, response body | 1 |

With the default, a client could get its answer **before** its data is saved. A client that immediately asks for the row could miss it. Worse, a commit that fails can no longer change the answer. We forced one: a table with a foreign key that is checked at commit time, and a route that inserts a row with no parent. The route itself succeeded.

- With `scope="request"`, the client got `200 {"saved": true}`. The commit then failed with `IntegrityError`, and the database had 0 rows.
- With `scope="function"`, the commit failed before the response, and the client got a 500. The database had 0 rows.

Both left the database right. Only the second told the client the truth. If your exit code can fail and the client needs to know, use `scope="function"`. If the exit code only closes things, such as this site's `get_store`, the default is fine.

More: [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/), the parts called "A dependency with `yield` and `try`" and "Early exit and `scope`".

## SQLite setup: PRAGMAs, WAL and creating tables

Here is `connect()` in `app/store.py`, trimmed to its steps.

```python
conn = sqlite3.connect(path, autocommit=True, check_same_thread=False, timeout=5.0)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA foreign_keys=ON")
conn.executescript(SCHEMA.read_text())
# ...insert the schema version if the table is empty...
conn.autocommit = False
conn.row_factory = sqlite3.Row
```

Take it line by line.

- **`autocommit=True` first, `False` last.** The `autocommit` setting exists in Python 3.12 and later. With it off (`autocommit=False`), a transaction is open from the moment you connect. A plain `sqlite3.connect(path)` does not do this: its default mode opens a transaction only at the first `INSERT`, `UPDATE` or `DELETE`, so you would not see the WAL error from a default connection. The code comment says why that matters for the two PRAGMAs, and we checked both. Inside that open transaction, `PRAGMA foreign_keys=ON` is accepted and does nothing: the value stays `0`. And `PRAGMA journal_mode=WAL` fails with `OperationalError: cannot change into wal mode from within a transaction`. With autocommit on, both work. So the PRAGMAs run first, and autocommit is switched off after.
- **`foreign_keys=ON`.** SQLite checks foreign keys only if you ask, and the default is off. We saw it: with the default, a row pointing at a parent that does not exist went in without a complaint. With the PRAGMA on, the same insert raised `IntegrityError: FOREIGN KEY constraint failed`. The setting belongs to the connection, not to the file. A brand new plain connection to the same file shows `0` again. That is why it is in `connect()`, which every request runs.
- **`journal_mode=WAL`.** This one is stored in the database file. We set it on one connection, closed it, opened a new plain connection, and it still said `wal`. It is the journal mode that the site's test suite also checks.
- **`timeout=5.0`.** How many seconds to wait when the database is locked by another connection. We tried two writers with a short timeout, and the second one failed with `database is locked`.
- **`check_same_thread=False`.** Explained in the previous section.
- **`executescript(SCHEMA...)`.** `app/schema.sql` is full of `CREATE TABLE IF NOT EXISTS`. Running it on every connect is safe, and it is this site's version of the tutorial's `create_all`. It runs per connection and not at a startup event.
- **`row_factory = sqlite3.Row`.** Rows come back as objects you can read by column name, and the store turns each into a `dict`.

Postgres does it differently. The tables are not created on each connect. A script does it once: `scripts/migrate.py` calls `apply_schema` with the direct Neon URL (more on that below), and prints `schema version 1`. `connect_pg` then expects the tables, and the `vector` extension, to exist already, because it calls `register_vector`.

More: the comments in `app/store.py`. The `sqlite3` module and `psycopg` are not covered by a source page in this site, so we link none. We ran the SQLite parts ourselves.

## Datetimes and placeholders

Two small rules make the same code work on both databases.

**Datetimes are ISO-8601 text in UTC.** Every timestamp is written with `datetime.now(UTC).isoformat()`, which gives text like `2026-10-14T18:23:10.593268+00:00`. Both schemas use `TEXT` for these columns, so the SQLite file and the Postgres tables hold the same strings.

Why not let the driver convert a `datetime`? We tried it. In Python 3.12 and later, `sqlite3`'s built-in `datetime` adapter is deprecated. It printed a `DeprecationWarning`, and what it stored was `typeof` `text` in a different shape: a space between date and time, and no time zone. It was the machine's local time, not UTC, so the same moment would be stored differently on two machines. With one fixed text format, two things hold. A comparison such as `due <= ?` in `due_cards` works as a plain text comparison, because the year comes first, then the month, and so on. And the values mean the same everywhere.

**Placeholders differ.** You never build SQL by gluing values into the string. You write a marker and pass the values separately. The marker depends on the driver.

| | `sqlite3` | `psycopg` |
| --- | --- | --- |
| marker | `?` | `%s` |
| module says | `paramstyle` is `qmark` | `paramstyle` is `pyformat` |
| example | `WHERE name = ?` | `WHERE name = %s` |

Both stores have the same query in them, `SELECT id FROM users WHERE name = ...`, with the marker changed. We checked the SQLite side. Using `%s` in `sqlite3` is a syntax error: `near "%": syntax error`. We also stored the text `x'); DROP TABLE n; --` through a `?` marker. It went in as plain text, and the table was untouched. A `%s` in psycopg is **not** Python string formatting. You still pass the values as a second argument, as in `conn.execute(sql, (name,))`.

The two files differ in a few other places, all visible in the code:

| Job | `SqliteStore` | `PostgresStore` |
| --- | --- | --- |
| get the new id | `cursor.lastrowid` | `INSERT ... RETURNING id` |
| insert unless it exists | `INSERT OR IGNORE` | `ON CONFLICT (name) DO NOTHING` |
| a yes/no value | `int(correct)` into an `INTEGER` with `CHECK (... IN (0, 1))` | a real `BOOLEAN` |
| read a key inside JSON text | `json_extract(data_json, '$.lesson_id')` | `data_json::jsonb ->> 'lesson_id'` |
| id column | `INTEGER PRIMARY KEY` | `BIGSERIAL PRIMARY KEY` |

We did not run the Postgres column of that table. There is no Postgres on the machine where this lesson was written. We read it from `app/store_pg.py` and `app/pg_schema.sql`.

## Neon: pooled and direct URLs

The setup notes are in `docs/runbooks/neon.md`. Neon gives you two connection strings for one database.

- The **pooled** one has `-pooler` in the host name. It goes through PgBouncer in *transaction mode*. This is the app's `DATABASE_URL`.
- The **direct** one connects straight to Postgres. It is `DATABASE_URL_UNPOOLED`, and `scripts/migrate.py` uses it for schema changes. The code comment on `apply_schema` says DDL through PgBouncer can fail.

Why does transaction mode matter to you? The runbook says this mode has no session `SET`. The reason is that a pooler in this mode may hand your next transaction to a different server connection, so a plain `SET something = ...` can be gone by the next statement. The runbook and the docstring of `connect_pg` give the rule: never use a session-level `SET`. Use **`SET LOCAL`** inside a transaction. `SET LOCAL` lasts until the transaction ends.

Two honest limits. First, we could not run the pooler here, so this part comes from the runbook and the code comments, not from our own run. Second, the one real use of `SET LOCAL` in this repo is in `app/ingest/search.py`. The tutor's `hybrid_search` runs `SET LOCAL hnsw.ef_search = 100` (and, for a filtered search, `SET LOCAL hnsw.iterative_scan = relaxed_order`) before its query and commits after it. Read that function to see the rule used in a route-sized piece of code. It is a Postgres-only path, and we did not run it against a server.

Two small things in `app/store_pg.py` follow from autocommit being off, as it is by default in psycopg.

- `connect_pg` calls `conn.commit()` right after `register_vector`. The comment says why: that call looks up types in a transaction, and the connection should not sit idle inside it.
- `PostgresStore._all` commits after each statement and rolls back on an error, just like the SQLite `_write`.

One more difference to know. In `sqlite3`, `with conn:` commits or rolls back but **does not close** the connection. We checked: after the `with` block, the connection still ran queries. In psycopg 3.3.6, leaving a `with` block on a connection also commits or rolls back, and then it **closes** the connection, unless the connection came from a pool (we read this in the installed package's `Connection.__exit__`; we did not run it against a server). That is why `apply_schema` can use `with PgConn.connect(...) as conn:` and has no `close()`. The same habit in `sqlite3` would leak a connection.

More: `docs/runbooks/neon.md` in this repo.

Sources (FastAPI 0.143.0, MIT licence, © 2018 Sebastián Ramírez; adapted and rewritten): [SQL (Relational) Databases](https://fastapi.tiangolo.com/tutorial/sql-databases/), [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/), [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/), [Concurrency and async / await](https://fastapi.tiangolo.com/async/). The SQLite, psycopg 3.3.6 and Neon parts come from this site's own code and runbook and from our own runs; no pages from those projects were copied. This site is not affiliated with FastAPI.
