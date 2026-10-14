import time

import anyio
from fastapi import FastAPI

app = FastAPI()


def slow_lookup() -> str:
    """Stands in for a library that blocks: a sync HTTP client or a sync database driver.
    It is a plain function, and you cannot change how the library works. Leave it as it is."""
    time.sleep(0.3)
    return "found"


async def fetch_rate() -> float:
    """Stands in for a library that you `await`: an async HTTP client. Leave it as it is."""
    await anyio.sleep(0.3)
    return 1.25


# A plain `def`: FastAPI runs it in a worker thread, so the blocking call does not stall the loop.
# (The other fix: keep `async def` and `return {"result": await run_in_threadpool(slow_lookup)}`.)
@app.get("/lookup")
def lookup() -> dict[str, str]:
    return {"result": slow_lookup()}


# `async def`, because the function it calls must be awaited.
@app.get("/rate")
async def rate() -> dict[str, float]:
    return {"rate": await fetch_rate()}
