# Task: a user API that never leaks a password

Open `workspace/fa4-responses-and-errors/api.py`. It has a tiny user API with an in-memory store. The store keeps the **full** record of each user, password included, so any route that returns it as it is will leak. Your job is to make the API safe and to give it proper status codes and errors.

## 1. Two models

Write two Pydantic models:

- `UserIn` has `name`, `email` and `password`. All three are `str`.
- `UserOut` has `id` (`int`), `name` and `email`. It has **no** password.

## 2. `POST /users/` creates a user

- The body is a `UserIn`.
- The route stores the user (the starter code shows how) and returns it as a `UserOut`.
- The status code is **201**. Use `status.HTTP_201_CREATED`.
- The response must not contain the password. Let FastAPI filter it with the output model. Do not delete the key by hand.

## 3. `GET /users/{user_id}` reads a user

- A known id returns the user as a `UserOut`, with status 200.
- An unknown id must **raise** `HTTPException` with status **404** and `detail="user not found"`.

## 4. A custom exception with a handler

`POST /orders/{item}` is already written. It raises `OutOfStock(item)` when the item has no stock left.

- Define the exception class `OutOfStock`. It stores the item name in `self.item`.
- Register a handler for it with `@app.exception_handler`. The handler returns a `JSONResponse` with status **409** and the body `{"detail": "<item> is out of stock"}`, for example `{"detail": "pear is out of stock"}`.

## 5. A safe validation error

FastAPI's default 422 body repeats the request body in an `input` key. A signup that has a password but no email would get its password sent back.

Register a handler for `RequestValidationError` that keeps the status **422** and returns

```json
{"detail": [{"loc": ["body", "email"], "msg": "Field required"}]}
```

That means one entry per problem, with only `loc` and `msg`. Build it from `exc.errors()`. The `loc` must stay a list.

## Check your work

The hidden tests use a test client. They check the status codes and the `detail` texts, and they check that the password never appears in any response body: not on create, not on read, and not on a 422. If a test fails, look at the raw response and ask: which part of my code decided this field would be there?
