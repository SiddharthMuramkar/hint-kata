# Task: write tests that catch a bug

This time you do not write the app. You write the tests.

Your workspace has two small apps with the same two routes:

- `GET /items/{item_id}` returns one item.
- `POST /items/` creates an item. Its `price` must be above zero.

`good_app.py` is correct. `buggy_app.py` has two bugs: an unknown id gives status 200 instead of 404, and the price rule is missing. Do not edit either app.

Your job is to fill in `test_items.py` so that it:

1. **passes** against `good_app`, and
2. **fails** against `buggy_app`.

A test that always passes is useless. The checker runs your file twice, once for each app. The app is picked by the `APP_MODULE` setting, which the starter already reads with `importlib.import_module(...)`. You can also run it yourself:

```console
$ APP_MODULE=good_app uv run pytest -q test_items.py
$ APP_MODULE=buggy_app uv run pytest -q test_items.py
```

The first command should be green. The second should show at least one failure.

## What the checker needs

- At least 3 test functions in `test_items.py`.
- Exit code 0 when run against `good_app`.
- A non-zero exit code when run against `buggy_app`.

## Hints

- Start with the happy path: `GET /items/1`.
- What should `GET /items/9999` return? Check the status code and the body.
- Send a bad `POST` and look at the status code. Which code does FastAPI use for invalid input?
- After a `POST`, can you read the item back with a `GET`? Use a new `id` in each test, because the apps keep items in memory.
