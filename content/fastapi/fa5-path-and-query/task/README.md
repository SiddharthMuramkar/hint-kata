# Task: a small book-search API

Open `workspace/fa5-path-and-query/api.py`. It has a small FastAPI app with three routes that take
anything. Your job is to make FastAPI convert and check the parameters for you. You do not need
an `if` for any of the rules below. Put them on the parameters.

## 1. Route order

Add `GET /books/featured`. It returns `{"featured": "Dune"}`.

The app already has `GET /books/{book_id}`. Put your new route in the right place relative to it.
If `/books/featured` answers with a 422, the order is wrong.

## 2. A path parameter with a rule

In `GET /books/{book_id}`, `book_id` must be an integer that is `1` or more. The route returns
`{"book_id": book_id}`. A value that breaks the rule must give a `422` whose `loc` is
`["path", "book_id"]`.

## 3. An Enum path value

Write a class `Shelf` that inherits from `str` and `Enum`. It has three members: `fiction`,
`science` and `history`. Their values are the same words in lower case.

Use it as the type of `shelf` in `GET /shelves/{shelf}`. The route returns
`{"shelf": "<the value as text>"}`. Any other shelf name is a `422`.

## 4. Query parameters on `GET /search`

| Parameter | Rule |
| --- | --- |
| `q` | Required text. At least 3 and at most 20 characters. |
| `tags` | Optional. A list of texts. `None` when the client sends none. |
| `limit` | Whole number. Default `10`. From `1` to `50`. |
| `sort` | Text. Default `"title"`. Must be exactly `title` or `year`. |
| `in_stock` | `bool`. Default `False`. |

The route returns:

```json
{"q": "dune", "tags": ["a", "b"], "limit": 10, "sort": "title", "in_stock": false}
```

## Check your work

The hidden tests call your routes with a test client. They check the status codes and the `loc`
of each error, and they check that several errors come back together. If a test fails, ask
yourself: did I leave this check to FastAPI, or did I try to do it myself?
