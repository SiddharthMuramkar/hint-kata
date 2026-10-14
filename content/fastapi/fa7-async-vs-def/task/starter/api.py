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


# TODO 1 (blocking call in `async def`): this route blocks the event loop for 0.3 s, so three
#   requests at once take 0.9 s and everything else on the server waits too. Fix it in one of
#   two ways. Make the route a plain `def`, or keep `async def` and call the blocking function
#   with `await run_in_threadpool(slow_lookup)` (from fastapi.concurrency).
@app.get("/lookup")
async def lookup() -> dict[str, str]:
    return {"result": slow_lookup()}


# TODO 2 (a coroutine nobody awaits): `fetch_rate()` is an `async def` function, so calling it
#   only creates a coroutine. This route is a plain `def`, so it cannot `await` it, and the
#   response body is wrong. Fix the route so that the client gets {"rate": 1.25}, and so that
#   several requests at once still overlap.
@app.get("/rate")
def rate() -> dict[str, float]:
    return {"rate": fetch_rate()}
