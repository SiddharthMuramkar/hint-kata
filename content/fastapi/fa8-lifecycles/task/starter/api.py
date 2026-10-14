from fastapi import FastAPI

# Every step of the fake pool writes one word here. The hidden tests read this list,
# so keep the name `EVENTS`.
EVENTS: list[str] = []


class FakeConnection:
    def query(self, sql: str) -> list[str]:
        return [f"result of {sql}"]


class FakePool:
    """A stand-in for a real connection pool. Do not change it."""

    def __init__(self) -> None:
        EVENTS.append("open")
        self.in_use = 0
        self.closed = False

    def checkout(self) -> FakeConnection:
        EVENTS.append("checkout")
        self.in_use += 1
        return FakeConnection()

    def release(self, conn: FakeConnection) -> None:
        EVENTS.append("release")
        self.in_use -= 1

    def close(self) -> None:
        EVENTS.append("close")
        self.closed = True


# TODO 1 (lifespan): write an async context manager called `lifespan(app)`.
#   - Before its `yield`: create one FakePool().
#   - Yield a dict that holds it, `{"pool": pool}`, so each request can read `request.state.pool`.
#   - After the `yield`: close the pool. Put the close in a `finally`.
#   Decorate it with @asynccontextmanager (from contextlib), then pass it to the app below:
#   `app = FastAPI(lifespan=lifespan)`.
app = FastAPI()


# TODO 2 (yield dependency): write `get_conn(request: Request)`, a dependency with `yield`.
#   - Take the pool from `request.state.pool`.
#   - Check out a connection with `pool.checkout()` and yield it.
#   - Give it back with `pool.release(conn)`, even when the route raises. Use try/finally.


# TODO 3 (route): add `GET /rows`.
#   - It takes the connection with Depends(get_conn) inside Annotated.
#   - It first does `EVENTS.append("route")`.
#   - It returns {"rows": conn.query("select 1")}.
