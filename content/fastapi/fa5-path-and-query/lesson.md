---
id: fa5-path-and-query
track: fastapi
title: "Path and query parameters with validation"
minutes: 25
pins:
  fastapi: "0.143.0"
sources:
  - fastapi-tutorial-path-params
  - fastapi-tutorial-query-params
  - fastapi-tutorial-query-params-str-validations
  - fastapi-tutorial-path-params-numeric-validations
---
Every request carries data in its URL. Some of it sits in the path, like the `3` in `/items/3`. Some of it comes after a `?`, like the `10` in `/items?limit=10`. In FastAPI you do not pick these apart by hand. You declare them as function parameters.

One sentence is the whole mental model: **FastAPI finds each parameter in the URL, turns the text into the type you wrote, checks the rules you attached, and only then calls your function.** If any step fails, your function never runs. The client gets a 422 response that says which parameter failed and why.

The rest of the lesson is detail on those steps: where a parameter comes from, how to give it a type and rules, and how to read the error.

## Path parameters and type conversion

Put a name in braces in the path. Then add a function parameter with the same name.

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
```

A request to `/items/3` calls `read_item(item_id=3)`. The URL holds the text `3`. FastAPI converts it to the Python `int` `3`, so the reply is `{"item_id": 3}` with no quote marks. Without the `: int`, the function would receive the string `"3"`.

The conversion can fail. A request to `/items/foo` or to `/items/4.2` gets status 422 and this body:

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["path", "item_id"],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "input": "foo"
    }
  ]
}
```

`read_item` did not run. The check happens before your code. The last section explains every field of this body.

Two more facts.

- `int` accepts any whole number. `/items/-5` gives `-5`, and `/items/007` gives `7`. If you want "1 or more", you need a rule. Rules come in a later section.
- A path parameter is always required, because it is part of the URL. Giving it a default does not make it optional: `/items/` with nothing after the slash simply does not match the route. And `item_id: Annotated[int, Path()] = 5` is refused with an `AssertionError` as soon as the route is declared.

More: [Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/).

## Route order: fixed before variable

FastAPI checks your routes in the order you declare them. The first path that matches wins. A variable part such as `{user_id}` matches any text, including the word `me`.

Say you have a fixed path for "the current user" and a variable path for "a user by id". Declare the fixed one first.

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/users/me")
def read_me():
    return {"user": "the current user"}


@app.get("/users/{user_id}")
def read_user(user_id: int):
    return {"user_id": user_id}
```

With this order, `/users/me` reaches `read_me`, and `/users/5` reaches `read_user`.

Now swap the two. `/users/me` matches `/users/{user_id}` first, and what the client sees depends on the type.

- With `user_id: int`, the client gets a 422, because `"me"` is not an integer. FastAPI does not go on to try the next route. `read_me` never runs.
- With `user_id: str`, the client gets `{"user_id": "me"}` and a status of 200. Nothing fails, and the answer is wrong. This is the worse bug.

The same rule covers a path you declare twice. The first declaration wins, and the second one is never used.

Routes with a different number of segments do not collide. `/users/me/items` still works even if `/users/{user_id}` comes first, because the second one has only two segments.

The habit is easy: fixed paths first, variable paths after.

More: [Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/), the part called "Order matters".

## Enum path values

Sometimes only a few values make sense. Make a class that inherits from both `str` and `Enum`, and use it as the type.

```python
from enum import Enum

from fastapi import FastAPI

app = FastAPI()


class Size(str, Enum):
    small = "small"
    medium = "medium"
    large = "large"


@app.get("/pizzas/{size}")
def read_pizza(size: Size):
    if size is Size.large:
        return {"size": size, "note": "Share it."}
    return {"size": size, "note": f"A {size.value} one."}
```

- `/pizzas/small` gives `{"size": "small", "note": "A small one."}`.
- `/pizzas/huge` gives a 422. The error has `type` `enum`, `loc` `["path", "size"]`, and a message that lists the allowed values: `Input should be 'small', 'medium' or 'large'`.
- The match is exact. `/pizzas/Large` is also a 422.

Inside the function, `size` is an enum member, not a plain string. You can compare it with `Size.large`, and you can get the text with `size.value`. If you return a member, FastAPI sends its value, so the JSON shows `"large"`.

Because the class also inherits from `str`, the generated API docs know the values are strings and list the three allowed ones.

On Python 3.11 and later, `StrEnum` from the `enum` module is a shorthand for the same pair, and ruff may suggest it. Written as `class Size(StrEnum)`, it behaves the same way in FastAPI.

More: [Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/), the part called "Predefined values".

## Query parameters: optional, required, defaults

A function parameter that is not in the path is a query parameter. The query string is everything after the `?`, as `key=value` pairs joined by `&`. Query values are text too, so they get the same conversion and the same checks as path values.

Whether a query parameter is required depends only on its default.

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/items/{item_id}")
def read_item(item_id: str, needy: str, skip: int = 0, limit: int | None = None):
    return {"item_id": item_id, "needy": needy, "skip": skip, "limit": limit}
```

- `needy` has no default, so it is required.
- `skip` has a default of `0`, so it is optional. If the client leaves it out, the function gets `0`.
- `limit` has a default of `None`, so it is optional, and `None` means "not sent". The `| None` is for your editor and for readers. The `= None` is what makes it optional.

| Request | What happens |
| --- | --- |
| `/items/foo` | 422. The error has `type` `missing` and `loc` `["query", "needy"]`. |
| `/items/foo?needy=x` | `skip` is `0` and `limit` is `None`. |
| `/items/foo?needy=x&skip=3&limit=7` | `skip` is `3` and `limit` is `7`. |
| `/items/foo?needy=x&skip=abc` | 422. The error has `type` `int_parsing` and `loc` `["query", "skip"]`. |

Three small facts that surprise people.

- Required means "must be present", not "must have text". `?needy=` gives `needy == ""`.
- An empty value for a number is not "use the default". `?skip=` is a 422.
- A key you did not declare, like `?bogus=1`, is ignored.

More: [Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/).

## Bool and list query values

**Bool.** Declare `short: bool = False` and FastAPI converts the text.

- These mean true: `1`, `true`, `on`, `yes`.
- These mean false: `0`, `false`, `off`, `no`.
- Upper and lower case both work, so `YES` and `Off` are fine.
- Anything else is a 422 with `type` `bool_parsing` and `loc` `["query", "short"]`. For example `maybe`, `2` and an empty value.

The query-params page says any other value becomes `False`. When we ran FastAPI 0.143.0, the answer was a 422. Trust the run, and test it in your own app before you rely on either.

**Lists.** To let a client repeat a key, use `Query()` and a list type.

```python
from typing import Annotated

from fastapi import FastAPI, Query

app = FastAPI()


@app.get("/search")
def search(tags: Annotated[list[str] | None, Query()] = None):
    return {"tags": tags}
```

- `/search?tags=a&tags=b` gives `{"tags": ["a", "b"]}`.
- `/search` gives `{"tags": null}`.
- `/search?tags=a,b` gives `{"tags": ["a,b"]}`. Commas do not split anything. It is one item.

The `Query()` is not optional decoration. Without it (`tags: list[str] | None = None`), FastAPI reads a `list` parameter from the request body, not from the URL. The `?tags=` part is ignored and `tags` stays `None`.

The items are converted too. With `list[int]`, the request `?ids=1&ids=x` is a 422, and `loc` includes the position of the bad item: `["query", "ids", 1]`. A plain `list` with no item type checks nothing about the items.

More: [Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/) for bool conversion, and [Query Parameters and String Validations](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/) for lists.

## Rules with Query and Path

A type says "an `int`". A rule says "an `int` that is 1 or more". You attach rules with `Query()` for query parameters and `Path()` for path parameters. Both go inside `Annotated`.

`Annotated[int, Path(ge=1)]` has two parts, as in lesson FA1. `int` is the type your editor sees. `Path(ge=1)` is the instruction for FastAPI.

```python
from typing import Annotated

from fastapi import FastAPI, Path, Query

app = FastAPI()


@app.get("/books/{book_id}")
def read_book(
    book_id: Annotated[int, Path(ge=1)],
    q: Annotated[str | None, Query(min_length=3, max_length=20)] = None,
    rating: Annotated[float, Query(gt=0, lt=5)] = 1.0,
):
    return {"book_id": book_id, "q": q, "rating": rating}
```

`Query` and `Path` take the same rules.

| Rule | For | The value must be | Error `type` when it is not |
| --- | --- | --- | --- |
| `min_length` | strings | at least this many characters | `string_too_short` |
| `max_length` | strings | at most this many characters | `string_too_long` |
| `pattern` | strings | a match for this regular expression | `string_pattern_mismatch` |
| `gt` | numbers | greater than | `greater_than` |
| `ge` | numbers | greater than or equal to | `greater_than_equal` |
| `lt` | numbers | less than | `less_than` |
| `le` | numbers | less than or equal to | `less_than_equal` |

What to remember about them.

- The edge matters. `ge=1` accepts `1` and rejects `0`. For a float, `gt=0` accepts `0.5` and rejects `0`.
- A value outside the rule is rejected, never fixed. `limit=500` with `le=100` is a 422. It does not become `100`.
- `pattern` is not anchored. `pattern="cat"` accepts `concatenate`. Write `^` and `$` when the whole value must match, as in `pattern="^(title|year)$"`.
- An empty value is still a value. `?q=` with `min_length=3` is a 422.
- Required or optional is still decided by the default, as before. `q: Annotated[str, Query(min_length=3)]` has no default, so it is required. Add `= None` and it is optional.
- Set the default with `=`, never with `Query(default=...)` inside `Annotated`. FastAPI raises an `AssertionError` for `Annotated[str, Query(default="rick")] = "morty"`, because it is unclear which default you mean.

Older code puts `Query` in the default position: `q: str | None = Query(default=None, max_length=5)`. That still works, but now the real Python default is a `Query` object. If you call the function yourself, outside FastAPI, you get that object and not `None`. With `Annotated` the default is an ordinary default.

You can name a rule once and reuse it, the same trick as in FA1.

```python
Limit = Annotated[int, Query(ge=1, le=100)]
```

Then `limit: Limit = 10` in one route and `limit: Limit = 20` in another both get the rule, with their own defaults.

The rules also go into the generated API docs. For example `min_length=3` shows up as `minLength: 3` in the OpenAPI schema.

More: [Query Parameters and String Validations](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/) for strings, and [Path Parameters and Numeric Validations](https://fastapi.tiangolo.com/tutorial/path-params-numeric-validations/) for numbers and `Path`.

## Alias and deprecated

Sometimes the name in the URL cannot be a Python name. `item-query` has a hyphen. Use `alias`.

```python
from typing import Annotated

from fastapi import FastAPI, Query

app = FastAPI()


@app.get("/items/")
def read_items(
    item_query: Annotated[str | None, Query(alias="item-query")] = None,
    q: Annotated[str | None, Query(deprecated=True)] = None,
):
    return {"item_query": item_query, "q": q}
```

- `/items/?item-query=foo` gives `item_query == "foo"`.
- `/items/?item_query=foo` gives `item_query == None`. Once there is an alias, FastAPI looks for the alias only. It does not look for the Python name, and it does not complain.
- Errors use the alias. A bad value gives `loc` `["query", "item-query"]`.

`deprecated=True` is for a parameter you want clients to stop using, while some still do. The parameter keeps working exactly as before. `/items/?q=old` is a normal 200. The only change is in the generated OpenAPI schema, where the parameter is marked `deprecated: true`, so the API docs show it as deprecated.

A common use is a rename. Keep the old parameter with `deprecated=True`, add the new one next to it, and remove the old one when no client uses it.

More: [Query Parameters and String Validations](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/), the parts called "Alias parameters" and "Deprecating parameters".

## Reading a 422

When a check fails, FastAPI answers with status 422 before your function runs. Here is a request that breaks two rules at once. The route is:

```python
from typing import Annotated

from fastapi import FastAPI, Query

app = FastAPI()


@app.get("/items/{item_id}")
def read_item(item_id: int, limit: Annotated[int, Query(le=100)] = 10):
    return {"item_id": item_id, "limit": limit}
```

The request is `GET /items/abc?limit=500`. The reply is:

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["path", "item_id"],
      "msg": "Input should be a valid integer, unable to parse string as an integer",
      "input": "abc"
    },
    {
      "type": "less_than_equal",
      "loc": ["query", "limit"],
      "msg": "Input should be less than or equal to 100",
      "input": "500",
      "ctx": {"le": 100}
    }
  ]
}
```

How to read it.

- `detail` is a list with one entry for each problem. FastAPI checks all the parameters and reports every failure together, so a client can fix them in one go.
- `type` is a short code for the kind of failure. You have met these: `missing`, `int_parsing`, `bool_parsing`, `enum`, `string_too_short`, `string_too_long`, `string_pattern_mismatch`, `greater_than`, `greater_than_equal`, `less_than` and `less_than_equal`.
- `loc` says where. The first item is the place, `path` or `query` in this lesson. The second is the parameter name, or its alias if it has one. A third item, a number, is a position in a list.
- `msg` is a sentence for people.
- `input` is what the client sent. It is the raw text, which is why it is `"500"` and not `500`. For a missing value it is `null`.
- `ctx` appears for some errors. It holds the value of the rule, here `le` is `100`.

The checks are done by Pydantic, under the hood.

Two ways to use this. A client developer reads `loc` to learn which parameter to fix. A test checks the status code and `loc`, and does not depend on the exact `msg` text. The hands-on task below does exactly that.

More: [Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/), the part called "Data validation", and [Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/), the part called "Required query parameters".

Sources: [Path Parameters](https://fastapi.tiangolo.com/tutorial/path-params/), [Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/), [Query Parameters and String Validations](https://fastapi.tiangolo.com/tutorial/query-params-str-validations/) and [Path Parameters and Numeric Validations](https://fastapi.tiangolo.com/tutorial/path-params-numeric-validations/). FastAPI 0.143.0 documentation, MIT licence, © 2018 Sebastián Ramírez. Adapted and rewritten. This site is not affiliated with FastAPI.
