import time

import anyio
import api  # the learner's api.py, on PYTHONPATH
import httpx

DELAY = 0.3  # how long slow_lookup and fetch_rate wait
CALLS = 3  # requests sent at the same moment
# Run one after the other, CALLS requests need CALLS * DELAY = 0.9 s. Run together, about 0.3 s.
# The limit sits well above the second number and below the first, so a slow runner still passes.
LIMIT = 0.75 * CALLS * DELAY


async def _send_together(path: str) -> tuple[float, list[httpx.Response]]:
    # raise_app_exceptions=False: a crash in a route becomes a 500 response, not a test error
    transport = httpx.ASGITransport(app=api.app, raise_app_exceptions=False)
    responses: list[httpx.Response] = []
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get(path)  # warm-up: the first request pays for lazy imports and caches

        async def one() -> None:
            responses.append(await client.get(path))

        start = time.perf_counter()
        async with anyio.create_task_group() as tg:
            for _ in range(CALLS):
                tg.start_soon(one)
        return time.perf_counter() - start, responses


def send_together(path: str) -> tuple[float, list[httpx.Response]]:
    return anyio.run(_send_together, path)


def test_slow_lookup_is_left_as_a_blocking_function():
    start = time.perf_counter()
    assert api.slow_lookup() == "found"  # a plain call, not a coroutine
    assert time.perf_counter() - start >= DELAY * 0.9, "keep the blocking sleep in slow_lookup"


def test_lookup_returns_its_result():
    elapsed, responses = send_together("/lookup")
    assert all(r.status_code == 200 for r in responses)
    assert all(r.json() == {"result": "found"} for r in responses)
    assert elapsed >= DELAY * 0.9, "the route must still call slow_lookup"


def test_lookup_requests_overlap():
    elapsed, _ = send_together("/lookup")
    assert elapsed < LIMIT, (
        f"{CALLS} requests took {elapsed:.2f} s. They ran one after another, so the blocking "
        "call is holding up the event loop. Move it off the loop."
    )


def test_rate_returns_a_number():
    _, responses = send_together("/rate")
    codes = [r.status_code for r in responses]
    assert codes == [200] * CALLS, f"status codes {codes}: the route must await fetch_rate()"
    assert all(r.json() == {"rate": 1.25} for r in responses)


def test_rate_requests_overlap():
    elapsed, responses = send_together("/rate")
    assert all(r.status_code == 200 for r in responses)
    assert elapsed >= DELAY * 0.9, "the route must still wait for fetch_rate()"
    assert elapsed < LIMIT, f"{CALLS} requests took {elapsed:.2f} s; they should overlap"
