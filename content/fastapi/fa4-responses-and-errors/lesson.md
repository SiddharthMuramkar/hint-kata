---
id: fa4-responses-and-errors
track: fastapi
title: "Response models, status codes and errors"
minutes: 25
pins:
  fastapi: "0.143.0"
sources:
  - fastapi-tutorial-response-model
  - fastapi-tutorial-response-status-code
  - fastapi-tutorial-handling-errors
  - fastapi-tutorial-extra-models
---

So far you have focused on what comes into a route. This lesson is about what goes out. Three decisions shape every response: which fields the client sees, which status code it gets, and what an error looks like. FastAPI lets you state each one in code, and then it does the work and writes the docs for you.

The examples use a tiny user API. The models are plain Pydantic models.

```python
from pydantic import BaseModel


class UserIn(BaseModel):
    name: str
    email: str
    password: str


class UserOut(BaseModel):
    name: str
    email: str
```

`UserIn` is what a client sends when it signs up. `UserOut` is what the client may see afterwards. The only difference is the `password` field, and that difference is the whole point of the lesson.

## The return type is the contract

Annotate the return type of a route function and FastAPI treats it as a promise about the response body. It uses that promise in three ways.

First, it **filters**. Only the fields named in the annotation can leave your app. Second, it **validates** what you return. Third, it adds a JSON Schema for the response to the OpenAPI document, so the automatic docs show the exact shape.

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/me")
def read_me() -> UserOut:
    # the dict has an extra key, and the annotation drops it
    return {"name": "Ann", "email": "ann@example.com", "password": "hunter2"}
```

A client gets `{"name": "Ann", "email": "ann@example.com"}`. The password never reaches the wire.

Validation works in the other direction too. If the function returns a dict without `email`, FastAPI does not send half an answer. It raises a server error and the client gets a 500. That is deliberate: a response that breaks the contract is a bug in your code, not in the client's request, so it must not look like a success.

Sometimes the value you return does not match the type you want documented, for example when you return a database row. Then use the decorator parameter `response_model` and annotate the function with `Any`.

```python
from typing import Any


@app.get("/me2", response_model=UserOut)
def read_me2() -> Any:
    return {"name": "Ann", "email": "ann@example.com", "password": "hunter2"}
```

If both a return annotation and `response_model` are present, `response_model` wins. You can also set `response_model=None` to switch response modelling off for one route, which you need when the annotation is something Pydantic cannot describe, such as `Response | dict`.

Read more: [Response Model - Return Type](https://fastapi.tiangolo.com/tutorial/response-model/).

## Input models and output models

A common mistake is to use one model for everything. Look at this route.

```python
@app.post("/users/")
def create_user(user: UserIn) -> UserIn:  # leaks the password
    return user
```

The client sends a password and the same password comes straight back. Worse, if another route returns `UserIn`, every client of that route gets passwords. The fix is to keep **separate models for separate jobs**: one for input that may carry a password, one for output that never does.

```python
@app.post("/users/", response_model=UserOut)
def create_user(user: UserIn) -> Any:
    return user  # FastAPI filters it down to UserOut
```

This is safe, but `Any` hides the real type from your editor. There is a tidier way. Put the shared fields in a base class and let the input model extend it. Annotate with the base class.

```python
class BaseUser(BaseModel):
    name: str
    email: str


class UserIn(BaseUser):
    password: str


@app.post("/users/")
def create_user(user: UserIn) -> BaseUser:
    return user
```

To your editor and type checker this is correct, because a `UserIn` is a `BaseUser`. To FastAPI it is a filter: it serializes only the fields of `BaseUser`, even though inheritance alone would allow more. You get type hints and safety together.

A real app often needs a third model, for the database. It holds a `hashed_password`, never the plain one. A user flows through three shapes: `UserIn` arrives, a `UserInDB` is stored, and `UserOut` is returned. Never store a plain password. Store a secure hash.

### Leaving out defaults

Another filter is about values, not fields. Say a model has defaults and you do not want them in the JSON.

```python
class Item(BaseModel):
    name: str
    tax: float = 10.5
    note: str | None = None


@app.get("/items/{item_id}", response_model=Item, response_model_exclude_unset=True)
def read_item(item_id: str):
    return {"name": "Foo"}  # response: {"name": "Foo"}
```

`response_model_exclude_unset=True` drops every field the data did not set. The word is *set*, not *different from the default*. If your data explicitly says `tax: 10.5`, the field was set, so it stays in the response. There are two close cousins: `response_model_exclude_defaults` and `response_model_exclude_none`.

The parameters `response_model_include` and `response_model_exclude` take a set of field names. They are quick, but the generated docs still show the full model. Separate models are better because the docs then tell the truth.

Read more: [Extra Models](https://fastapi.tiangolo.com/tutorial/extra-models/) and [Response Model - Return Type](https://fastapi.tiangolo.com/tutorial/response-model/#return-type-and-data-filtering).

## Choosing the status code

Every response has a three-digit status code, and the default is 200. Set another with the `status_code` parameter of the decorator. Like `response_model`, it belongs to `@app.post(...)` and friends, not to your function.

```python
from fastapi import status


@app.post("/users/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: UserIn) -> Any:
    return user
```

`status.HTTP_201_CREATED` is just the number 201 with a readable name. Your editor can complete it, so you do not have to remember codes. Plain `201` works the same.

The ranges are worth knowing:

- 2xx means success. 200 is the default, 201 means "created" and fits a `POST` that adds a record, and 204 means "no content", so the response must have no body.
- 4xx means the client made a mistake. 404 is "not found", 409 is "conflict", and 422 is what FastAPI sends for invalid input.
- 5xx means your server failed. You almost never pick these yourself.

The code is also written into the OpenAPI document, so the docs show a 201 for this route instead of a 200.

Read more: [Response Status Code](https://fastapi.tiangolo.com/tutorial/response-status-code/).

## Raising HTTPException

When a request cannot succeed, you do not `return` an error. You `raise` `HTTPException`. It is a normal Python exception, so it stops the function at once, even when you raise it deep inside a helper that the route called.

```python
from fastapi import HTTPException

USERS = {1: UserOut(name="Ann", email="ann@example.com")}


@app.get("/users/{user_id}")
def read_user(user_id: int) -> UserOut:
    if user_id not in USERS:
        raise HTTPException(status_code=404, detail="user not found")
    return USERS[user_id]
```

For an unknown id the client sees status 404 and the body `{"detail": "user not found"}`. The `detail` can be any JSON-friendly value, such as a dict or a list, not only a string.

You can also pass `headers=` to add response headers to the error. This is rare, but some security schemes need it.

```python
raise HTTPException(
    status_code=404,
    detail="user not found",
    headers={"X-Error": "user"},
)
```

Notice the contract idea from the first section still holds. The success path returns `UserOut`. Errors take a different path, and they do not have to fit the response model.

Read more: [Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/).

## Overriding error handlers

Sometimes `HTTPException` is not the right tool. Your business code may raise its own exception, and you want it to become a clean response in one place. Define the exception, then register a handler for it.

```python
from fastapi import Request
from fastapi.responses import JSONResponse


class OutOfStock(Exception):
    def __init__(self, sku: str) -> None:
        self.sku = sku


@app.exception_handler(OutOfStock)
def out_of_stock_handler(request: Request, exc: OutOfStock) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": f"{exc.sku} is out of stock"})
```

Any route, or any helper it calls, can now `raise OutOfStock("apple")` and the client gets a 409 with that JSON. The route code stays free of response details.

FastAPI also has default handlers for two cases: an `HTTPException` and invalid request data. You can replace either one. Invalid data raises `RequestValidationError`, and its default answer is a 422 with a `detail` list. Each entry has a `loc` that says where the problem is, and a `msg`. Perhaps your clients expect another shape.

```python
from fastapi.exceptions import RequestValidationError


@app.exception_handler(RequestValidationError)
def on_invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
    problems = [
        {"field": ".".join(str(part) for part in e["loc"]), "problem": e["msg"]}
        for e in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"errors": problems})
```

Build the answer from `exc.errors()`, one entry at a time. Do not return `str(exc)`, because the text can reveal details about your code.

There is a second reason to care. Each entry in the default 422 body also carries an `input` key, and for a missing field that key holds the **whole request body**. A signup request that has a password but no email would get its password echoed straight back. Picking only `loc` and `msg`, as the handler above does, closes that hole.

One detail about `HTTPException`: FastAPI has its own class, and it extends Starlette's. When you register a handler, register it for Starlette's class (`from starlette.exceptions import HTTPException as StarletteHTTPException`). Then it also catches errors raised by Starlette itself, such as the 404 for a URL that does not exist at all.

Read more: [Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/#install-custom-exception-handlers).

## A checklist for every route

Before you call a route done, run through these questions.

- Does the route declare what it returns, with a return type or `response_model`?
- Does the output model leave out secrets such as passwords, tokens and internal ids?
- Are input and output different models wherever the two differ?
- Does `POST` that creates something answer 201, and does a delete with no body answer 204?
- Does every "not found" or "not allowed" case `raise HTTPException` with a status code and a useful `detail`?
- Do business failures use one custom exception with one handler, so the status code is decided in one place?
- Did you test the failures too: the 404, the 409, the 422, and a check that no response body contains the password, error bodies included?

Sources (FastAPI 0.143.0, MIT licence, © 2018 Sebastián Ramírez; adapted and rewritten): [Response Model - Return Type](https://fastapi.tiangolo.com/tutorial/response-model/), [Response Status Code](https://fastapi.tiangolo.com/tutorial/response-status-code/), [Handling Errors](https://fastapi.tiangolo.com/tutorial/handling-errors/), [Extra Models](https://fastapi.tiangolo.com/tutorial/extra-models/).
