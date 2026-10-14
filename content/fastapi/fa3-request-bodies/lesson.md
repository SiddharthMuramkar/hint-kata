---
id: fa3-request-bodies
track: fastapi
title: "Request bodies with Pydantic models"
minutes: 25
pins:
  fastapi: "0.143.0"
  pydantic: "2"
sources:
  - fastapi-tutorial-body
  - fastapi-tutorial-body-nested-models
  - fastapi-tutorial-body-fields
  - fastapi-tutorial-body-multiple-params
---

Path and query parameters are good for small values, like an id or a page number. Real clients
also send bigger things: a new book, an order, a profile. That data travels in the request body.
In FastAPI you describe a body with a Pydantic model, and the framework does the boring work
for you. This lesson shows how, and what the errors look like when the data is wrong.

All the examples use one small library app.

## Why a body is a model

A **request body** is data the client sends along with the request. A **response body** is what
your API sends back. Most routes send a response body. Only some need to read a request body.
Use `POST`, `PUT`, `PATCH` or `DELETE` for that. A `GET` with a body is allowed by FastAPI, but
it is discouraged: the docs page will not show it, and proxies may drop it.

You could take the body as a plain `dict` and check every key by hand. That gets long fast, and
you will forget a case. A Pydantic model says the same thing once, in a class.

```python
from pydantic import BaseModel


class Book(BaseModel):
    title: str
    pages: int
    in_stock: bool = True
```

Read it like a form. `title` and `pages` have no default, so they are required. `in_stock` has a
default, so a client may leave it out. Write `str | None = None` for a field that may be
missing when you have no better default.

Declaring the model buys you four things without extra code:

- **Validation.** Bad data is rejected before your function runs.
- **Conversion.** A JSON string such as `"412"` becomes the int `412` when the field is an `int`.
- **Docs.** The model becomes a JSON Schema in the OpenAPI document. The `/docs` page shows it
  and lets you try the route.
- **Editor help.** Inside the route you get a `Book` object, so your editor can complete
  `book.pages` and warn you about typos.

If you took a `dict` instead, you would get none of these. The last section comes back to that.

Read more: [Request Body](https://fastapi.tiangolo.com/tutorial/body/).

## Declaring a body parameter

To use the model, give a function parameter that type. That is all.

```python
from fastapi import FastAPI

app = FastAPI()


@app.post("/books/", status_code=201)
def add_book(book: Book):
    return {"title": book.title, "pages": book.pages}
```

FastAPI sees that `Book` is a Pydantic model, so it takes `book` from the request body. For
every request it then does these steps, in this order:

1. It reads the body as JSON.
2. It checks each field against the model and converts types where it can.
3. If anything is wrong, it stops and answers `422`. Your function is never called.
4. If all is well, it calls your function with a real `Book` object.

The route above sets `status_code=201`, the usual code for "created". Without it, the answer
would be `200`.

Inside the function, use the object like any other: `book.title`, `book.pages`. To turn it back
into a dict, call `book.model_dump()`.

**What a 422 looks like.** Suppose a client sends `{"title": "Dune", "pages": "many"}`. The
answer has status `422` and a JSON body like this:

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["body", "pages"],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "input": "many"
    }
  ]
}
```

Each entry in `detail` is one problem. `loc` is the path to the bad value. It starts with where
the value was found (`"body"`, `"query"` or `"path"`), then the field names. `type` is a stable
code, `msg` is a sentence for humans, and `input` is what the client sent. FastAPI collects all
the problems in one pass, so a client with three mistakes sees all three at once.

Conversion is gentle, but it is not magic. `"412"` becomes `412`. The float `2.5` for an `int`
field is an error, because it would lose the `.5`.

Read more: [Request Body](https://fastapi.tiangolo.com/tutorial/body/).

## Nested models and lists

A field type can be another model. A field type can also be a list. That lets you describe the
JSON your clients really send.

```python
from pydantic import BaseModel


class Author(BaseModel):
    name: str
    born: int | None = None


class Review(BaseModel):
    stars: int
    text: str = ""


class Book(BaseModel):
    title: str
    pages: int
    author: Author
    tags: list[str] = []
    reviews: list[Review] = []
```

This model expects JSON like the example below. Each model becomes one JSON object.

```json
{
  "title": "Dune",
  "pages": 412,
  "author": {"name": "Herbert"},
  "tags": ["scifi"],
  "reviews": [{"stars": 5}]
}
```

Validation goes all the way down. The inner models get the same checks, conversion, docs and
editor help, however deep they go.

The `loc` of an error shows the way in. A missing author name has the `loc`
`["body", "author", "name"]`. A bad second review has the `loc` `["body", "reviews", 1, "stars"]`.
List positions are numbers and counting starts at 0, so `1` means the second review. Read `loc`
from left to right, like a path.

Always give a list a type inside the brackets. `list[str]` checks every element. A bare `list`
accepts anything, and the docs show an array of unknown things.

When order and repeats do not matter, `set[str]` is a good type for tags. It turns duplicates
into one value.

Read more: [Body - Nested Models](https://fastapi.tiangolo.com/tutorial/body-nested-models/).

## Field constraints and examples

A type alone says little. A page count must be above zero, a title must not be empty, a star
rating is 1 to 5. Put these rules on the field with Pydantic's `Field`.

```python
from pydantic import BaseModel, Field


class Review(BaseModel):
    stars: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=500)


class Book(BaseModel):
    title: str = Field(min_length=1, examples=["Dune"])
    pages: int = Field(gt=0, description="Number of pages")
    author: Author
```

`Field` takes the same kind of arguments as `Query`, `Path` and `Body`: `gt`, `ge`, `lt` and
`le` for numbers, and `min_length`, `max_length` and `pattern` for strings. Pass `default=` to
give the field a default value. Pass nothing for a required field.

`Field` has a second job: extra information for the docs. `description` and `title` appear in
the generated schema. `examples` shows a sample value on the `/docs` page, which helps people who
read your API.

A broken rule gives a normal `422`, with a type that names the rule and the limit:

```json
{
  "type": "greater_than",
  "loc": ["body", "pages"],
  "msg": "Input should be greater than 0",
  "input": 0,
  "ctx": {"gt": 0}
}
```

Two things to remember. First, import `Field` from `pydantic`, not from `fastapi`. FastAPI has
`Query`, `Path`, `Body` and others, but it has no `Field`, so that import fails. Second, extra
keys you pass to `Field` end up in the OpenAPI document. Some strict OpenAPI tools may not like
keys outside the standard, so keep to the usual ones unless you need more.

Read more: [Body - Fields](https://fastapi.tiangolo.com/tutorial/body-fields/).

## Several body parameters

A route can have path, query and body parameters together. FastAPI decides where each one comes
from by three rules:

1. If the name appears in the path (`{book_id}`), it is a **path** parameter.
2. If the type is a simple type (`int`, `str`, `bool`, `float`), it is a **query** parameter.
3. If the type is a Pydantic model, it is a **body** parameter.

```python
@app.put("/books/{book_id}")
def replace_book(book_id: int, book: Book, dry_run: bool = False):
    return {"book_id": book_id, "dry_run": dry_run, "title": book.title}
```

Here `book_id` comes from the path, `dry_run` from the query string (`?dry_run=true`), and `book`
from the body. Each part is checked on its own, and its error `loc` starts with `"path"`,
`"query"` or `"body"` to match.

**Two or more models.** A request has only one body, but your route may ask for two models.
FastAPI then expects one JSON object with one key per parameter name.

```python
class Shelf(BaseModel):
    room: str


@app.put("/shelve/{book_id}")
def shelve(book_id: int, book: Book, shelf: Shelf): ...
```

The client now sends `{"book": {...}, "shelf": {"room": "A"}}`. The keys are the parameter names.
The inner objects are the same as before.

**A single value in the body.** A plain `int` is a query parameter by default. To read it from
the body, wrap it with `Body`.

```python
from typing import Annotated

from fastapi import Body


@app.put("/shelve/{book_id}")
def shelve(book_id: int, book: Book, copies: Annotated[int, Body(ge=1)]): ...
```

Now the JSON has `{"book": {...}, "copies": 2}`. `Body` takes the same rules as `Field`, like
`ge=1` here.

**Embed one model.** With only one model, the client sends its fields directly. To make it wrap
them in a key, as it does with several models, use `embed=True`.

```python
@app.put("/books/{book_id}")
def replace_book(book_id: int, book: Annotated[Book, Body(embed=True)]): ...
```

The client must now send `{"book": {"title": "Dune", ...}}`. Pick one style per route and
document it. A client that sends the wrong shape gets a `422` with the `loc` `["body", "book"]`.

If a body is optional, give the parameter a default: `book: Book | None = None`.

Read more: [Body - Multiple Parameters](https://fastapi.tiangolo.com/tutorial/body-multiple-params/).

## Common mistakes

Most body bugs are about the shape of the request, not about your Python. These are the ones
you will meet first.

**Sending a form instead of JSON.** A route that declares a model expects JSON. If a client posts
form data (`curl -d "title=Dune&pages=1"`, or `data=` in `httpx`), FastAPI does not read it as an
object. The answer is `422` with `loc: ["body"]` and the type `model_attributes_type`. Notice
that the `loc` stops at `"body"`. No field is named, because the whole body is the wrong kind of
thing. Send JSON instead (`json=` in `httpx`).

**Forgetting the Content-Type header.** FastAPI reads the body as JSON when the request says
`Content-Type: application/json`. In FastAPI 0.143.0, a body without that header is treated as
plain text. Even a perfectly valid JSON string then fails with the same `422` and `loc: ["body"]`.
With `curl`, add `-H "Content-Type: application/json"`. With `httpx` and `TestClient`, the
`json=` argument sets the header for you. If you pass `content=` yourself, set the header
yourself.

**Broken JSON.** A body like `{bad` with the right header gives `422` with the type
`json_invalid`. The error says the JSON could not be decoded.

**Using `dict` as the type.** `def add_book(data: dict)` works, and that is the problem. Any
JSON object passes, even `{"pages": "free"}`. Nothing is checked or converted, your code has to
test every key, and `/docs` shows an empty object. If you know the shape, write the model.

**A bare `list`, or a missing `embed`.** A field typed `list` does not check its items. And a
client that sends fields directly to a route that uses `embed=True` fails on `["body", "book"]`.
When you see a 422, read `loc` first. It nearly always tells you which of these it is.

A good habit is to test these cases. A short test for each error path, using `TestClient`, keeps
the shape of your API from changing by accident. In the task you do exactly that.

Read more: [Request Body](https://fastapi.tiangolo.com/tutorial/body/).

Sources (FastAPI 0.143.0, MIT licence, © 2018 Sebastián Ramírez; adapted and rewritten): [Request Body](https://fastapi.tiangolo.com/tutorial/body/), [Body - Nested Models](https://fastapi.tiangolo.com/tutorial/body-nested-models/), [Body - Fields](https://fastapi.tiangolo.com/tutorial/body-fields/), [Body - Multiple Parameters](https://fastapi.tiangolo.com/tutorial/body-multiple-params/). This site is not affiliated with FastAPI or Pydantic.
