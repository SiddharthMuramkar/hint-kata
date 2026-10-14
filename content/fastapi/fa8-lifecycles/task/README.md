# Task: a connection pool with a lifespan

Open `workspace/fa8-lifecycles/api.py`. It has a fake connection pool, `FakePool`. Every step of the
pool (`open`, `checkout`, `release`, `close`) writes one word into the list `EVENTS`. Your job is to
tie the pool to the right lifetimes, so the words come out in the right order. Do not change the
pool class.

The two lifetimes:

- The **pool** lives as long as the app. Open it once at start-up and close it once at shutdown.
- A **connection** lives as long as one request. Check it out when the request starts and give it
  back when the request is over, even when the route fails.

## 1. A lifespan for the pool

Write an async context manager called `lifespan(app)` and pass it to `FastAPI(lifespan=...)`.

- Before the `yield`, create a `FakePool()`.
- Yield `{"pool": pool}`. That puts the pool in the lifespan state, so each request can read it as
  `request.state.pool`.
- After the `yield`, call `pool.close()`. Put it in a `finally`.

## 2. A yield dependency for the connection

Write `get_conn(request: Request)`. It reads the pool from `request.state.pool`, checks out a
connection with `pool.checkout()`, and yields it. It gives the connection back with
`pool.release(conn)` in a `finally`, so the connection is released even when the route raises.

## 3. A route that uses it

Add `GET /rows`. It takes the connection through `Depends(get_conn)`. It adds the word `route` to
`EVENTS` and returns `{"rows": conn.query("select 1")}`.

For one request, `EVENTS` should read: `open`, `checkout`, `route`, `release`, and then `close` when
the app shuts down.

## Check your work

The hidden tests use `with TestClient(app)`, so the lifespan runs. They compare the whole `EVENTS`
list, for a normal request, for several requests, and for routes that raise an error. They also
check that the pool was reached through the lifespan state. If a test fails, print `api.EVENTS` and
look at which word is missing, extra, or in the wrong place.
