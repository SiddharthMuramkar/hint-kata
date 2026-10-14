---
id: fa8-lifecycles
track: fastapi
title: "Resource lifecycles: yield dependencies, scope, lifespan"
minutes: 25
pins:
  fastapi: "0.143.0"
sources:
  - fastapi-tutorial-dependencies-with-yield
  - fastapi-advanced-advanced-dependencies
  - fastapi-advanced-events
  - fastapi-advanced-async-tests
---

Some things in an app need care at both ends. A database connection must be opened and later given back. A connection pool must be built once and shut down once. If the "give back" step is skipped on one path, say because a route raised, you leak the resource.

One sentence is the whole mental model: **every resource has a lifetime, and FastAPI gives you two places to tie code to it. A `yield` dependency covers things that live as long as one request. The `lifespan` covers things that live as long as the app.** In both, the code before `yield` is set-up and the code after it is tear-down.

Lesson FA1 introduced `yield` dependencies. This lesson is about the details that bite: what the tear-down can see, when it runs, in what order, and how to test it. We check each claim the same way, with a list of events. Every code block here was run on FastAPI 0.143.0, and the event lists you see are what we got.

## Yield dependencies: set-up and tear-down

A dependency that uses `yield` instead of `return` is a pair. The code up to the `yield` runs before your route. The value you yield is what the route receives. The code after the `yield` is the tear-down.

```python
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()
EVENTS: list[str] = []


def get_session() -> Iterator[str]:
    EVENTS.append("set-up")
    try:
        yield "session"
    finally:
        EVENTS.append("tear-down")


@app.get("/ping")
def ping(session: Annotated[str, Depends(get_session)]):
    EVENTS.append("route")
    return {"session": session}
```

After one request, `EVENTS` is `["set-up", "route", "tear-down"]`.

- Yield exactly once per dependency. The docs say so.
- A plain `def` and an `async def` both work. FastAPI handles each the way it handles a normal dependency.
- Under the hood, FastAPI treats the function like a Python context manager (the kind you use with `with`). You do not add `@contextmanager` yourself.

The `try/finally` is not decoration. It is what makes the tear-down run when something goes wrong. The next section shows why.

A habit for the rest of the lesson: write the steps into a list, like `EVENTS`, and compare the list in a test. A list shows order. A `print` does not survive a test run.

More: [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/).

## What the tear-down sees: exceptions

If the route raises, FastAPI throws that exception into your dependency, at the line of the `yield`. So `try`, `except` and `finally` work as in any Python function. We wrote a dependency that records what reaches it.

```python
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

app = FastAPI()
EVENTS: list[str] = []


class Boom(Exception):
    pass


def get_session() -> Iterator[str]:
    EVENTS.append("set-up")
    try:
        yield "session"
    except BaseException as exc:
        EVENTS.append(f"saw {type(exc).__name__}")
        raise
    else:
        EVENTS.append("no exception")
    finally:
        EVENTS.append("finally")


@app.get("/ok")
def ok(session: Annotated[str, Depends(get_session)]):
    EVENTS.append("route")
    return "ok"


@app.get("/boom")
def boom(session: Annotated[str, Depends(get_session)]):
    EVENTS.append("route")
    raise Boom("x")


@app.get("/missing")
def missing(session: Annotated[str, Depends(get_session)]):
    EVENTS.append("route")
    raise HTTPException(status_code=404, detail="nope")
```

| Request | Client gets | `EVENTS` |
| --- | --- | --- |
| `/ok` | 200 | `set-up`, `route`, `no exception`, `finally` |
| `/boom` | 500 | `set-up`, `route`, `saw Boom`, `finally` |
| `/missing` | 404 | `set-up`, `route`, `saw HTTPException`, `finally` |

Two things to take from the table.

- An `HTTPException` from the route reaches the dependency too, not only your own exception types. It is just another exception to the `yield` line.
- `finally` runs on every row. So put the "give it back" step in `finally`. Use `except` only when you want to react to a specific kind of failure, such as rolling back.

Now the part that goes wrong in real code. What if the dependency catches the exception and does not raise it again?

```python
def get_session() -> Iterator[str]:
    try:
        yield "session"
    except HTTPException:
        EVENTS.append("swallowed")
```

When the route raises `HTTPException(404)`, this dependency catches it and ends quietly. FastAPI never learns that there was an error. The client gets **500**, not 404. The docs add that the server logs nothing, so you have a 500 and no clue why. The same happens with any exception you catch and drop.

You have two good choices inside an `except`.

- Put a bare `raise` at the end, to pass the same exception on.
- Raise a different exception on purpose. This dependency turns a `Boom` from the route into a 400 for the client:

```python
def get_session() -> Iterator[str]:
    try:
        yield "session"
    except Boom as exc:
        raise HTTPException(status_code=400, detail=f"Owner error: {exc}") from exc
```

A route that raises `Boom("b")` now gives the client `400` and `{"detail": "Owner error: b"}`. The docs call this a somewhat advanced technique. Most of the time, raise `HTTPException` in the route itself.

More: [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/), the parts called "A dependency with yield and try" and "Always raise in dependencies with yield and except".

## Scope: before or after the response

When does the tear-down run, relative to the response going out? You choose, with the `scope` argument of `Depends`.

- `scope="request"` is the default for a `yield` dependency. Tear-down runs after the response has been sent.
- `scope="function"` runs the tear-down as soon as the route function returns, before the response is sent. This scope was added in FastAPI 0.121.

To see the difference we wrapped the app in a tiny ASGI function that writes `response sent` into the list when the last piece of the body goes out. ASGI is the interface between the server and FastAPI.

```python
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()
EVENTS: list[str] = []


def get_session() -> Iterator[str]:
    EVENTS.append("set-up")
    try:
        yield "session"
    finally:
        EVENTS.append("tear-down")


@app.get("/request-scope")
def request_scope(session: Annotated[str, Depends(get_session)]):
    EVENTS.append("route")
    return "ok"


@app.get("/function-scope")
def function_scope(session: Annotated[str, Depends(get_session, scope="function")]):
    EVENTS.append("route")
    return "ok"


class MarkSent:
    def __init__(self, inner) -> None:
        self.inner = inner

    async def __call__(self, scope, receive, send):
        async def send_and_mark(message):
            if message["type"] == "http.response.body" and not message.get("more_body"):
                EVENTS.append("response sent")
            await send(message)

        await self.inner(scope, receive, send_and_mark)
```

We served `MarkSent(app)` and made one request to each route.

| Route | `EVENTS` |
| --- | --- |
| `/request-scope` | `set-up`, `route`, `response sent`, `tear-down` |
| `/function-scope` | `set-up`, `route`, `tear-down`, `response sent` |

Use `scope="function"` when you do not need the resource after the route returns, and the response is slow to send. The docs' example is a database connection that a slow streaming response would otherwise hold. Keep the default when the response itself still uses the resource, as a streaming response that reads from it does.

The scope also decides what an exception in the tear-down can do. We made a dependency that raises `HTTPException(400)` after its `yield`, on a request where the route succeeded.

- With the default scope, the client had already received its **200**. The exception cannot change that. On the server side, the run raised `RuntimeError: Caught handled exception, but response already started.`
- With `scope="function"`, the client got the **400**, because the response had not gone out yet.

So if your tear-down can fail and the client must hear about it, that is a reason to use `scope="function"`.

One more observation, on the error path. With the default scope, when the route raised, the tear-down ran before the error response went out: `saw Boom` and `finally` came before the 500. That fits the docs' sequence diagram, where the exception passes through the dependency first and the error response is built after.

### The scope rule

A dependency can only depend on dependencies that outlive its own tear-down, because its exit code may still use them. That gives one rule. A request-scoped dependency cannot depend on a function-scoped one. Here is what FastAPI 0.143.0 did with a request-scoped `outer` that depends on a function-scoped `inner`:

```python
def inner() -> Iterator[str]:
    yield "inner"


def outer(i: Annotated[str, Depends(inner, scope="function")]) -> Iterator[str]:
    yield "outer"


@app.get("/bad")
def bad(o: Annotated[str, Depends(outer)]):
    return o
```

The error came when the route was declared, before any request: `DependencyScopeError: The dependency "outer" has a scope of "request", it cannot depend on dependencies with scope "function".` The other direction works. A function-scoped dependency may depend on request-scoped ones. In our run, that gave `inner set-up`, `outer set-up`, `route`, `outer tear-down`, `inner tear-down`.

### Old advice

Search results may still show older advice, because this behaviour moved. Per the docs: before 0.106 the tear-down ran after the response and could not change it. From 0.106 it ran before the response was sent. In 0.118 that was reverted to after-the-response, because a streaming response could no longer use a resource that was already closed. In 0.121 `scope` arrived so you can pick. If you read an old answer, check the version it talks about.

More: [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/), the parts called "Early exit and scope" and "Scope for sub-dependencies", and [Advanced Dependencies](https://fastapi.tiangolo.com/advanced/advanced-dependencies/), the part called "Dependencies with yield and scope".

## Several yield dependencies: tear-down in reverse

Dependencies can depend on each other, and each can use `yield`. Say `c` depends on `b`, and `b` depends on `a`.

```python
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()
EVENTS: list[str] = []


def dep_a() -> Iterator[None]:
    EVENTS.append("a set-up")
    try:
        yield
    finally:
        EVENTS.append("a tear-down")


def dep_b(a: Annotated[None, Depends(dep_a)]) -> Iterator[None]:
    EVENTS.append("b set-up")
    try:
        yield
    finally:
        EVENTS.append("b tear-down")


def dep_c(b: Annotated[None, Depends(dep_b)]) -> Iterator[None]:
    EVENTS.append("c set-up")
    try:
        yield
    finally:
        EVENTS.append("c tear-down")


@app.get("/chain")
def chain(c: Annotated[None, Depends(dep_c)]):
    EVENTS.append("route")
```

One request gives: `a set-up`, `b set-up`, `c set-up`, `route`, `c tear-down`, `b tear-down`, `a tear-down`. Set-up goes from the deepest dependency up. Tear-down goes back the other way, so `c` can still use `b` while it cleans up.

Three more results from our runs.

- **Siblings.** A route with `x: Depends(sib_x)` and `y: Depends(sib_y)` set up `x` then `y`, in the order of the parameters. It tore down `y` then `x`.
- **One run per request.** If `a` is needed twice in the same tree, FastAPI still runs it once. That is the dependency cache, and `use_cache=False` turns it off. In our run, that gave two `a set-up` entries and two `a tear-down` entries.
- **A failure in the middle.** If `b` raises `HTTPException(503)` before its own `yield`, the client gets the 503. `a` already started, so its tear-down runs: `a set-up`, `b set-up raises`, `a tear-down`. `b` never reached its `yield`, so `b` has no tear-down.

More: [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/), the part called "Sub-dependencies with yield".

## Lifespan: set-up and tear-down for the whole app

A `yield` dependency runs for every request. Some resources should be built once, like a connection pool, an HTTP client or a loaded model. For those, use the app's lifespan: an async function with one `yield`, wrapped with `@asynccontextmanager` and passed to `FastAPI(lifespan=...)`.

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

EVENTS: list[str] = []


class Client:
    def close(self) -> None:
        EVENTS.append("close client")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    EVENTS.append("open client")
    client = Client()
    app.state.client = client
    try:
        yield
    finally:
        client.close()


app = FastAPI(lifespan=lifespan)
```

The code before the `yield` runs once, before the app takes its first request. The code after it runs once, when the app shuts down, after the last request. The function gets the `app` as its argument.

Compared with a dependency, the differences are the whole point:

| | `yield` dependency | lifespan |
| --- | --- | --- |
| Runs | for each request | once per app start |
| Good for | a connection checked out for one request | a pool, a client, a loaded model |
| Declared | `Depends(...)` in the route | `FastAPI(lifespan=...)` |

If the code before the `yield` raises, the app does not start, and the code after the `yield` does not run. In our run the error reached the test client, and the list held only the first step. So open resources one at a time, and protect each with its own `try/finally` or `with` once it is open.

### Lifespan or events, not both

Before lifespan, you wrote two separate functions, `@app.on_event("startup")` and `@app.on_event("shutdown")`. They still work in 0.143.0. An app with only those handlers ran both of them in our test. But they are deprecated: Python printed `DeprecationWarning: on_event is deprecated, use lifespan event handlers instead.` Two separate functions also cannot share a local variable, so you end up with globals.

The docs say it is all lifespan or all events. We checked: with `lifespan=` set and an `on_event` startup and shutdown handler registered too, the list showed only the lifespan's start and stop. The handlers never ran. So do not leave an old `on_event` behind when you add a lifespan, because it silently stops working.

More: [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).

## Lifespan state and request.state

The lifespan builds the resource. How does a route get it? There are two ways, and we ran both.

**Yield a dict.** Give the `yield` a dictionary. Its entries become the app's lifespan state, and each request sees them as attributes of `request.state`.

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[dict[str, Client]]:
    client = Client()
    try:
        yield {"client": client}
    finally:
        client.close()


app = FastAPI(lifespan=lifespan)


@app.get("/who")
def who(request: Request):
    return {"client": type(request.state.client).__name__}
```

The FastAPI docs send you to the [Starlette lifespan page](https://starlette.dev/lifespan/) for this feature, so that is the place to read the details. Our run showed one more fact. Each request gets its own `request.state`. An attribute set on it in one request was not there in the next. Only the entries from the yielded dict are shared.

**Use `app.state`.** Set `app.state.client = client` before the `yield`, as in the first lifespan above, and read it in a route with `request.app.state.client`. This also worked in our run. The yielded dict keeps the resource tied to the lifespan that owns it, so this lesson uses it from here on.

### Putting the two lifetimes together

The common pattern uses both. The lifespan builds a thing that is expensive and shared. A `yield` dependency borrows from it for one request, and hands it back.

```python
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request


class Session:
    pass


def get_session(request: Request) -> Iterator[Session]:
    client = request.state.client
    session = client.begin()
    try:
        yield session
    finally:
        client.end(session)
```

With a `Client` that has `begin` and `end` methods that record their steps, two requests to a route that uses `get_session` gave this list:

`open client`, `begin`, `route`, `end`, `begin`, `route`, `end`, `close client`.

The client is opened once and closed once. Each request begins and ends its own session. A route that raised still got its `end`, because the `end` sits in a `finally`. The hands-on task asks you to build this shape with a pool.

More: [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/), and the Starlette [Lifespan](https://starlette.dev/lifespan/) page for state.

## Testing lifespan code

Tests are where lifespan code gets forgotten, because a bare test client does not run it.

- `TestClient(app)` on its own does **not** run the lifespan. In our run no set-up step happened, and a route that read `request.state` failed with a 500.
- `with TestClient(app) as client:` runs the start-up when the block begins and the shutdown when it ends. This is the form to use. It also means the shutdown steps are only in your event list *after* the block.
- `httpx.AsyncClient` with `ASGITransport(app=app)` does not run the lifespan either. In our run, the same route raised `AttributeError: 'State' object has no attribute 'client'`. The async tests page names the `asgi-lifespan` package and its `LifespanManager` for this. We did not run that package.

A test of the full order then looks like this. The list is cleared first, and the checks use the whole list, so a missing or extra step shows up.

```python
def test_order() -> None:
    EVENTS.clear()
    with TestClient(app) as client:
        client.get("/ping")
        assert EVENTS == ["open client", "begin", "route", "end"]
    assert EVENTS[-1] == "close client"
```

Each `with` block starts the app again, so each test gets its own start-up and shutdown.

More: [Async Tests](https://fastapi.tiangolo.com/advanced/async-tests/), and lesson FA2 for `TestClient` and dependency overrides.

## How this site does it

This site is a FastAPI app, so it has the same two pieces.

**The `yield` dependency is `get_store`, in `app/deps.py`.** It opens a store with `open_store_from_settings()`, yields it inside a `try`, and calls `store.close()` in the `finally`. It uses the default scope, so the store closes after the response is sent. A route that asks for `Depends(get_store)` gets its own store for that request. `get_user_id` depends on `get_store` as well. When a route uses both, the dependency cache means only one store is opened. We counted: one request to `/` gave one open and one close.

**The lifespan is in `app/main.py`.** Before its `yield`, it starts Logfire when a token is set, loads the lessons and the sources into `app.state`, and writes the mastery settings to the store through a short-lived store that it closes in a `finally`. It yields nothing. It does not use lifespan state, and there are no tear-down steps after the `yield`. Each call to `open_store_from_settings()` opens one connection, to SQLite or to Postgres when `DATABASE_URL` is set. The site keeps no pool, so there is nothing to shut down after the `yield`.

That explains the site's tests. They use `with TestClient(app) as c`, so the lifespan runs and `app.state.lessons` exists. We tried a bare `TestClient(app)` and `GET /lessons/fa1-dependencies` gave a 500. Some tests also swap `get_store` for a fake with `app.dependency_overrides`, as lesson FA2 shows.

Sources (FastAPI 0.143.0, MIT licence, © 2018 Sebastián Ramírez; adapted and rewritten): [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/), [Advanced Dependencies](https://fastapi.tiangolo.com/advanced/advanced-dependencies/), [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/), [Async Tests](https://fastapi.tiangolo.com/advanced/async-tests/). This site is not affiliated with FastAPI.
