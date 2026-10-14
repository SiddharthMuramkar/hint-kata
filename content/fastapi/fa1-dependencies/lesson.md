---
id: fa1-dependencies
track: fastapi
title: "Dependencies"
minutes: 25
pins:
  fastapi: "0.143.0"
sources:
  - fastapi-tutorial-dependencies
  - fastapi-tutorial-classes-as-dependencies
  - fastapi-tutorial-dependencies-with-yield
  - fastapi-advanced-testing-dependencies
---
You already know that FastAPI reads your route function's parameters and fills them from the request. A path parameter comes from the URL. A query parameter comes from the query string. A body parameter comes from the JSON.

Dependencies use the same idea one level down. One sentence is the whole mental model: **a dependency is a function that FastAPI calls for you, and its own parameters are filled in the same way as a route's parameters.** Keep that sentence in mind and the rest of this lesson is detail.

## What Depends does

Say three routes all need the same query options. Without a dependency you repeat the parameters and the logic in every route. With a dependency you write them once.

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


def common_filters(q: str | None = None, sort: str = "name"):
    return {"q": q, "sort": sort}


@app.get("/items/")
def list_items(filters: Annotated[dict, Depends(common_filters)]):
    return filters
```

Read `Depends(common_filters)` as "before you run `list_items`, call `common_filters` and give me what it returns as `filters`". Two details matter.

- You pass the function itself, with no brackets. FastAPI is the one that calls it. If you wrote `common_filters()` you would be calling it yourself, once, when the module loads.
- The call happens on every request, not once when the app starts. A request to `/items/?q=cat` gives `filters == {"q": "cat", "sort": "name"}`.

Why bother? Shared logic lives in one place. And because routes only ask for a result, you can swap the dependency for a fake in tests, which the last section shows.

FastAPI also adds the dependency's parameters to the OpenAPI docs, so `q` and `sort` show up on `/docs` without extra work.

More: [Dependencies - First Steps](https://fastapi.tiangolo.com/tutorial/dependencies/).

## Annotated and reusable aliases

The `Annotated[T, Depends(fn)]` form says two things at once. `T` is the type your editor sees. `Depends(fn)` is the instruction for FastAPI. The two parts are independent, so you can name the pair and reuse it.

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


def common_filters(q: str | None = None, sort: str = "name") -> dict[str, str | None]:
    return {"q": q, "sort": sort}


Filters = Annotated[dict[str, str | None], Depends(common_filters)]


@app.get("/items/")
def list_items(filters: Filters):
    return filters


@app.get("/users/")
def list_users(filters: Filters):
    return filters
```

`Filters` is a normal Python name for a type. Every route that writes `filters: Filters` gets the same dependency and the same editor hints. If the dependency changes, you edit one line.

A dependency can be a normal `def` or an `async def`. FastAPI handles both, and you can mix them with sync or async routes.

More: [Dependencies - First Steps](https://fastapi.tiangolo.com/tutorial/dependencies/) covers `Annotated` aliases and the sync/async rule.

## Sub-dependencies and how parameters flow

A dependency can have its own dependencies. FastAPI builds a tree from the parameters and resolves it from the leaves up.

```python
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

app = FastAPI()


def get_token(token: str) -> str:
    return token


def get_user(token: Annotated[str, Depends(get_token)]) -> str:
    if token != "secret":
        raise HTTPException(status_code=401)
    return "alice"


@app.get("/me")
def read_me(user: Annotated[str, Depends(get_user)]):
    return {"user": user}
```

Follow one request, `GET /me?token=secret`.

1. FastAPI sees that `read_me` needs `get_user`.
2. It sees that `get_user` needs `get_token`.
3. `get_token` has a plain `token: str`, so it is a query parameter. FastAPI reads it from the request.
4. FastAPI calls `get_token`, passes the result to `get_user`, and passes that result to `read_me`.

The key point: `token` is declared on the function that uses it, and FastAPI reads it from the request there. The route does not declare `token` and pass it down. If `token` is missing, the client gets a 422, exactly as if `read_me` had asked for it.

If two dependencies in one request both need `get_token`, FastAPI calls it once and reuses the answer for the rest of that request. That cache lasts for one request only.

More: [Classes as Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/) has the picture of a tree of dependencies, and [Dependencies - First Steps](https://fastapi.tiangolo.com/tutorial/dependencies/) explains the idea of injection.

## Classes as dependencies

`Depends` needs a callable. A function is a callable. So is a class, because calling it makes an instance. FastAPI reads the parameters of `__init__` the same way it reads a function's.

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


class Pagination:
    def __init__(self, skip: int = 0, limit: int = 10):
        self.skip = skip
        self.limit = limit


@app.get("/items/")
def list_items(page: Annotated[Pagination, Depends()]):
    return {"skip": page.skip, "limit": page.limit}
```

With `Depends()` and no argument, FastAPI uses the type in `Annotated` as the callable. You could also write `Depends(Pagination)`. A request to `/items/?skip=2` gives `skip == 2` and `limit == 10`.

Why choose a class over a function that returns a dict? Your editor knows `page.skip` exists and is an `int`. A dict gives you string keys and no hints. A class can also carry small helper methods.

Choose a plain function when you only need one value, or when you need clean-up code with `yield`. A function with `yield` is the next section.

More: [Classes as Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/).

## Dependencies with yield

Sometimes a dependency needs set-up and tear-down: open a database session, hand it to the route, close it afterwards. Use `yield` instead of `return`. The code before `yield` is set-up. The value you yield is what gets injected. The code after `yield` is tear-down.

```python
from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()
LOG: list[str] = []


def get_db():
    LOG.append("open")
    try:
        yield "db-session"
    finally:
        LOG.append("close")


@app.get("/ping")
def ping(db: Annotated[str, Depends(get_db)]):
    LOG.append("route")
    return {"db": db}
```

After one request `LOG` is `["open", "route", "close"]`. Use `try` and `finally` so the tear-down runs even when the route raises. Use `yield` once per dependency.

With several yield dependencies in a chain, FastAPI runs the set-up from the leaf up, then the route. Tear-down runs in the opposite order, so a dependency can still use its sub-dependency while it cleans up.

### When does tear-down run?

This is the part people miss. By default a `yield` dependency has `scope="request"`. Its tear-down runs after the response has been sent to the client.

Since FastAPI 0.121 you can write `Depends(get_db, scope="function")`. Then tear-down runs as soon as the route function returns, before the response is sent. Use it when you do not need the resource after the route, for example to release a connection before a slow response goes out.

One rule follows from the order. A dependency with `scope="request"` cannot depend on one with `scope="function"`, because the inner one would close first. FastAPI raises an error while it builds the routes. The other direction is fine.

More: [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/), including the "Early exit and scope" part.

## Overriding dependencies in tests

Because routes only ask for a result, a test can hand them a different one. Every `FastAPI` app has a dictionary called `dependency_overrides`. The key is the original dependency function. The value is the replacement.

```python
from fastapi.testclient import TestClient


def fake_filters():
    return {"q": "test", "sort": "none"}


app.dependency_overrides[common_filters] = fake_filters
client = TestClient(app)
assert client.get("/items/").json() == {"q": "test", "sort": "none"}
app.dependency_overrides.clear()
```

The route code did not change. The replacement can have its own parameters too, and FastAPI resolves them the same way. Clear the dictionary when you finish so one test does not leak into the next.

Lesson FA2 goes deeper on testing. For now, remember that this swap is the payoff of the mental model: the route never called the dependency, so a test can change what it gets. The hands-on task below uses this idea too.

More: [Testing Dependencies with Overrides](https://fastapi.tiangolo.com/advanced/testing-dependencies/).

Sources: [Dependencies - First Steps](https://fastapi.tiangolo.com/tutorial/dependencies/), [Classes as Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/), [Dependencies with yield](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/) and [Testing Dependencies with Overrides](https://fastapi.tiangolo.com/advanced/testing-dependencies/). FastAPI 0.143.0 documentation, MIT licence, © 2018 Sebastián Ramírez. Adapted and rewritten. This site is not affiliated with FastAPI.
