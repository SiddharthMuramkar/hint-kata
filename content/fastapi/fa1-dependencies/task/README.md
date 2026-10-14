# Task: pagination and a database dependency

Open `api.py` in your workspace. It has a small FastAPI app with one route, `GET /items/`, and a list of fake items. Your job is to add two dependencies and use them in the route.

## 1. A `pagination` dependency

Write a function `pagination` that returns a dict `{"skip": ..., "limit": ...}`.

- `skip` is a query parameter. It is an integer, defaults to `0`, and must be `0` or more.
- `limit` is a query parameter. It is an integer, defaults to `10`, and must be between `1` and `100`.
- A value outside those bounds must give a `422` response. There is no clamping.

Let FastAPI do the checking. Put the rules on the parameters, for example with `Query(...)`.

## 2. A `get_db` dependency with `yield`

Write a function `get_db` that:

1. appends `"open"` to the module-level list `LOG`,
2. yields the `ITEMS` list (this stands in for a database),
3. appends `"close"` to `LOG` afterwards, even if the route raises.

After one request, `LOG` should be `["open", "close"]`.

## 3. Use both in the route

`GET /items/` must get its pagination and its "database" through `Depends`. It must not call either function itself. It returns:

```json
{"skip": 0, "limit": 10, "items": ["item-0", "item-1"]}
```

`items` is the slice `ITEMS[skip : skip + limit]` of whatever list `get_db` yielded.

## Check your work

The hidden tests call your route with a test client, check the `422` cases, check `LOG`, and replace each dependency with a fake using `app.dependency_overrides`. If a test fails, ask yourself: did the route get this value from FastAPI, or did I produce it myself?
