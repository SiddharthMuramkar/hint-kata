---
id: fa2-testing
track: fastapi
title: "Testing FastAPI apps"
minutes: 25
pins:
  fastapi: "0.143.0"
  httpx: "0.28.1"
sources:
  - fastapi-tutorial-testing
  - fastapi-advanced-testing-dependencies
  - fastapi-advanced-async-tests
---

A web app you cannot test is a web app you are afraid to change. FastAPI makes tests cheap: you
can call your routes from plain pytest functions, with no server and no network. This lesson
shows the tools and the few habits that keep tests honest.

All examples use one small app. It has a `get_db` dependency that hands each route a dict that
acts as a tiny database.

```python
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException

app = FastAPI()


def get_db() -> dict[int, str]:
    return {1: "apple", 2: "pear"}  # imagine a real database here


@app.get("/fruit/{fruit_id}")
def read_fruit(fruit_id: int, db: Annotated[dict[int, str], Depends(get_db)]):
    if fruit_id not in db:
        raise HTTPException(status_code=404, detail="Fruit not found")
    return {"id": fruit_id, "name": db[fruit_id]}
```

## Why TestClient needs no server

`TestClient` does not start uvicorn. It does not open a port. It takes your `app` object and
calls it directly, inside your own Python process. A FastAPI app is an ASGI app, which is just a
callable that receives a request description and sends back a response. The client builds that
description for you and reads the reply.

`TestClient` comes from Starlette and is built on `httpx`, so its methods feel like the ones in
`httpx` and `requests`: `client.get(...)`, `client.post(..., json=...)`, `response.json()`. You
must have `httpx` installed to use it. FastAPI re-exports it as `fastapi.testclient.TestClient`
for convenience.

Because nothing goes over a network, these tests are fast and do not collide with anything else
on your machine. They also run your real routing, validation and dependency code, which is the
point.

Read more: [Testing](https://fastapi.tiangolo.com/tutorial/testing/).

## Writing a first test

A test is a plain function whose name starts with `test_`. Create the client once, call a route,
and check the status code and the JSON body with ordinary `assert` statements.

```python
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_read_fruit() -> None:
    response = client.get("/fruit/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "name": "apple"}
```

Notice two things. The test is a normal `def`, not `async def`, even if your route is `async`.
And the call is a normal call, with no `await`. That is why you can use pytest without extra
plugins.

Sending data works like in `httpx`. Put path and query values in the URL, pass a dict to `json=`
for a JSON body, to `headers=` for headers and to `cookies=` for cookies.

Read more: [Testing](https://fastapi.tiangolo.com/tutorial/testing/).

## Testing error paths

Happy paths are the easy half. The bugs hide in the failures, so test them on purpose. Two kinds
matter.

The first kind is an error you raise yourself, like the 404 in our app. Check the status and the
`detail` message.

```python
def test_unknown_fruit_is_404() -> None:
    response = client.get("/fruit/99")
    assert response.status_code == 404
    assert response.json() == {"detail": "Fruit not found"}
```

The second kind is a request that fails validation. FastAPI answers with status 422 and a body
that lists what went wrong. Each entry in `detail` has a `loc` that says where the problem is
(`["path", "fruit_id"]`) and a `msg` that says why.

```python
def test_fruit_id_must_be_an_integer() -> None:
    response = client.get("/fruit/not-a-number")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "fruit_id"]
```

Assert on `loc` rather than on the whole message. The text of `msg` comes from the validation
library and can change between versions, while the location of the mistake stays stable.

Read more: [Testing, extended example](https://fastapi.tiangolo.com/tutorial/testing/#testing-extended-example).

## Overriding dependencies

Our `get_db` pretends to be a database. In a real app it would open a connection, and you do not
want that in a unit test. FastAPI lets you swap any dependency for a fake, only while testing.

Every app has a plain dict called `app.dependency_overrides`. The key is the original
dependency function. The value is the replacement. Once you set it, FastAPI calls the
replacement instead, and it skips the original and anything the original depends on.

```python
def fake_db() -> dict[int, str]:
    return {7: "plum"}


def test_read_fruit_with_fake_db() -> None:
    app.dependency_overrides[get_db] = fake_db
    try:
        response = client.get("/fruit/7")
        assert response.json() == {"id": 7, "name": "plum"}
    finally:
        app.dependency_overrides.clear()
```

The cleanup matters. The dict lives on the `app` object, and every test in the run shares that
object. If you forget to clear it, the fake leaks into the next test and you get failures that
depend on test order. A pytest fixture with `yield` is a neat home for this: set the override
before the `yield`, clear it after.

The override works wherever the dependency is used: in a route, in a router, or in a decorator.
The replacement can take its own parameters, such as query values, like any dependency.

Read more: [Testing Dependencies with Overrides](https://fastapi.tiangolo.com/advanced/testing-dependencies/).

## Lifespan and async tests

Two special cases need extra care.

**Lifespan.** If your app has a lifespan function (startup and shutdown code, for example opening
a connection pool), a bare `TestClient(app)` does not run it. Use the client as a context
manager. Startup runs when you enter the `with` block and shutdown runs when you leave it.

```python
def test_with_lifespan() -> None:
    with TestClient(app) as client:
        response = client.get("/fruit/1")
        assert response.status_code == 200
```

**Async tests.** Most of the time you do not need them. You need an `async def` test only when
the test itself must `await` something else, for example reading rows back through an async
database library after the request. An `async def` test cannot use `TestClient`, because that
client runs the event loop for you. Use `httpx.AsyncClient` with an `ASGITransport` that points
at your app, and mark the test for AnyIO.

```python
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.anyio
async def test_read_fruit_async() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/fruit/1")
    assert response.status_code == 200
```

The `base_url` is only a label, because no request leaves your process. One catch: `AsyncClient`
does not run lifespan events. If you need them in an async test, wrap the app in a lifespan
manager such as the `asgi-lifespan` package.

Read more: [Async Tests](https://fastapi.tiangolo.com/advanced/async-tests/).

## What to test

You cannot test everything, so pick well. A short checklist for each route:

- One happy path: the right status code and the right JSON body.
- Each error you raise yourself: 404, 409, 403 and so on.
- Bad input: a wrong type or a missing required field should give 422.
- Side effects: after a `POST`, can you read the new item back?
- Dependencies: replace databases and outside services with fakes, and clear them afterwards.
- Edge values: empty strings, zero, negative numbers, the largest allowed value.

A good test fails when the code is wrong. You can check that on purpose: break the route, run the
test, and watch it go red. In the task for this lesson you do exactly that. You write tests that
pass on a correct app and fail on a buggy one.

Read more: [Testing](https://fastapi.tiangolo.com/tutorial/testing/).

Sources (FastAPI 0.143.0, MIT licence; adapted and rewritten): [Testing](https://fastapi.tiangolo.com/tutorial/testing/), [Testing Dependencies with Overrides](https://fastapi.tiangolo.com/advanced/testing-dependencies/), [Async Tests](https://fastapi.tiangolo.com/advanced/async-tests/).
