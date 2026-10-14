from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[dict[str, FakePool]]:
    pool = FakePool()
    try:
        yield {"pool": pool}
    finally:
        pool.close()


app = FastAPI(lifespan=lifespan)


def get_conn(request: Request) -> Iterator[FakeConnection]:
    pool: FakePool = request.state.pool
    conn = pool.checkout()
    try:
        yield conn
    finally:
        pool.release(conn)


@app.get("/rows")
def read_rows(conn: Annotated[FakeConnection, Depends(get_conn)]) -> dict[str, list[str]]:
    EVENTS.append("route")
    return {"rows": conn.query("select 1")}
