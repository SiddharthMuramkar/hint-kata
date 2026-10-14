---
id: fa7-async-vs-def
track: fastapi
title: "async def vs def"
minutes: 25
pins:
  fastapi: "0.143.0"
sources:
  - fastapi-async
  - fastapi-tutorial-dependencies
---

A web server has many clients at once. FastAPI lets you write a route as `async def` or as a plain `def`. Both work, and both return the same answer when you test them one at a time. They differ when many requests arrive together and your code has to wait for something.

One sentence is the whole mental model: **a `def` route runs in a worker thread, and an `async def` route runs on the event loop itself, so it must never wait without `await`.**

The rest of the lesson explains that sentence, measures it with a small app, and then shows how this site follows it. We ran every number below on FastAPI 0.143.0 with Python 3.13, on a laptop. Your numbers will differ a little. The shape of the results will not.

## The event loop in one paragraph

The event loop is a piece of code that runs on one thread. It keeps a list of jobs. It runs one job until that job says "I have to wait for something", and the word for that is `await`. Then the loop picks up another job. When the thing the first job waited for is ready, that job goes back on the list. All the `async def` code in your server shares this one loop, so while one job runs, no other job runs. That is fine when jobs hand the loop back often. It is a problem when one job holds on. A call like `time.sleep(0.5)` does not hand the loop back. It makes the whole thread wait, and the loop lives on that thread.

FastAPI is built on Starlette, and Starlette is built on a library called AnyIO. The docs page says so, and you will see `anyio` in the code below. The page also tells the idea with a burger shop. It is worth a read.

More: [Concurrency and async / await](https://fastapi.tiangolo.com/async/).

## A plain def runs in a threadpool

When a route is a plain `def`, FastAPI does not call it on the loop. It hands the function to a pool of worker threads and waits for the answer. This is documented on the page above, in the part called "Path operation functions".

```python
import time

from fastapi import FastAPI

app = FastAPI()


@app.get("/def-sleep")
def def_sleep():
    time.sleep(0.5)  # blocks this worker thread, not the loop
    return {"ok": True}
```

While one worker thread sits in `time.sleep`, the loop is free. It can accept new requests and give them to other workers. So two requests at once overlap, and both finish after about half a second.

This is why a blocking library is fine in a `def` route. A sync HTTP client, a sync database driver, and a file read all just work.

The pool is not endless. We read its size with `anyio.to_thread.current_default_thread_limiter().total_tokens` and got 40. Then we sent 40 requests at once to a `def` route that sleeps for 0.5 s. The batch took 0.52 s. With 41 requests it took 1.01 s, because the 41st had to wait for a free thread. So a `def` route costs one thread for as long as it runs.

Threads help when code waits. They do not make Python calculate faster. The docs page treats number-crunching (the "CPU bound" kind) as a different problem from waiting.

More: [Concurrency and async / await](https://fastapi.tiangolo.com/async/).

## async def runs on the loop

When a route is `async def`, FastAPI calls it straight on the loop. There is no thread and no hand-off. That is cheap, and it is how one process can keep many requests that are all waiting.

The price is the rule from the mental model. Inside an `async def` function, nothing may block. These all block:

- `time.sleep(...)`.
- A sync HTTP client, such as `requests.get(...)` or `httpx.get(...)`.
- A sync database driver, such as `sqlite3` or `psycopg`.
- Reading a big file, or a long loop of calculation.

```python
@app.get("/async-sleep")
async def async_sleep():
    time.sleep(0.5)  # blocks the loop, and the loop serves everyone
    return {"ok": True}
```

The failure is quiet. In our run this route answered with status 200, no error and no warning. It was only slow, and it made everything else slow too.

We saw that on a real server. We started uvicorn on localhost, sent one request that blocked for 1 s, and 0.2 s later sent a request to a trivial `/ping` route. Three times in a row, the ping took 0.80 s. That is the rest of the blocked second. When the slow route was a `def`, or an `async def` that used `await anyio.sleep(1)`, the ping took 0.001 to 0.002 s.

## await and async libraries

`await` is how an `async def` function says "I am waiting, take the loop". It only works inside `async def`, and only on something awaitable, such as the result of calling another `async def` function.

To wait inside an async route, you need a library that was written for it. Some examples are `anyio.sleep`, `httpx.AsyncClient`, an async database driver, and the `run` method of a Pydantic AI agent. The docs page puts the rule in one line: if a library tells you to call it with `await`, make your route `async def`.

```python
import anyio


@app.get("/await-sleep")
async def await_sleep():
    await anyio.sleep(0.5)  # hands the loop back while it waits
    return {"ok": True}
```

There are two ways to get `await` wrong.

- **`await` in front of a normal call.** Python raises a `TypeError`, because the result of a normal call is not awaitable. In our run the error came after the call had finished, so the blocking had already happened. `await` does not turn a blocking call into a polite one.
- **No `await` in front of an async call.** You get a coroutine object, and nothing runs it. In a route this gave us a 500 response and a warning from Python: "coroutine ... was never awaited". The second route in the hands-on task has exactly this bug.

More: [Concurrency and async / await](https://fastapi.tiangolo.com/async/), the part called "async and await".

## What we measured

Here is the method, so that you can repeat it. We built one app with the three routes above, plus a fourth that keeps `async def` but calls `await run_in_threadpool(time.sleep, 0.5)`. We called it through `httpx.AsyncClient` with `ASGITransport(app)`, which runs the app inside the test process, with no network. We started N requests at the same moment as AnyIO tasks and timed the whole batch with `time.perf_counter()`. We repeated each batch 5 times and took the median.

```python
import time

import anyio
import httpx


async def timed(client: httpx.AsyncClient, path: str, calls: int) -> float:
    start = time.perf_counter()
    async with anyio.create_task_group() as tg:
        for _ in range(calls):
            tg.start_soon(client.get, path)
    return time.perf_counter() - start


async def main() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ("/def-sleep", "/async-sleep", "/await-sleep"):
            print(path, [round(await timed(client, path, n), 2) for n in (1, 2, 3)])


anyio.run(main)
```

Each route waits 0.5 s. This is how long the batch took, in seconds (median of 5):

| Route | 1 request | 2 at once | 3 at once |
| --- | --- | --- | --- |
| `def` + `time.sleep(0.5)` | 0.507 | 0.505 | 0.510 |
| `async def` + `time.sleep(0.5)` | 0.508 | 1.016 | 1.526 |
| `async def` + `await anyio.sleep(0.5)` | 0.502 | 0.502 | 0.503 |
| `async def` + `await run_in_threadpool(time.sleep, 0.5)` | 0.508 | 0.511 | 0.511 |

Read the second row. Each extra request adds half a second. That is "one after another", and it is what a blocked loop looks like. The other rows stay flat. That is "overlap".

The hands-on task uses the same trick, with 3 requests at once and a generous limit, so a slow computer still passes.

## Mixing def and async def

You can mix the two kinds in one app, and you can mix them inside one request. FastAPI calls two kinds of function for you: your route, and each dependency it uses. It looks at every one of them on its own and applies the same rule. A `def` dependency goes to a worker thread. An `async def` dependency runs on the loop. The docs say this on the async page, and the dependencies page says you may put `def` dependencies in `async def` routes and the other way round.

We checked where each piece ran with a small probe. It calls `asyncio.get_running_loop()`. If that works, the code runs on the loop. If it raises `RuntimeError`, the code runs in a worker thread.

| Piece | Where it ran |
| --- | --- |
| `async def` route | on the loop |
| `def` route | in a worker thread |
| `def` dependency (also under an `async def` route) | in a worker thread |
| `async def` dependency (also under a `def` route) | on the loop |
| a plain helper that you call yourself | wherever its caller runs |

The last row matters most. FastAPI does not wrap your own helper calls. A blocking helper called from an `async def` route blocks the loop. That is the first bug in the hands-on task.

Mixing also decides the timing. Here are two routes. Each has a dependency that blocks for 0.5 s:

```python
from typing import Annotated

from fastapi import Depends


def sync_dep() -> int:
    time.sleep(0.5)
    return 1


async def async_dep() -> int:
    time.sleep(0.5)
    return 1


@app.get("/async-route-sync-dep")
async def async_route(value: Annotated[int, Depends(sync_dep)]):
    return {"value": value}


@app.get("/def-route-async-dep")
def def_route(value: Annotated[int, Depends(async_dep)]):
    return {"value": value}
```

We sent 3 requests at once to each. The first route took 0.51 s, so the requests overlapped. The `def` dependency ran in worker threads, even though the route itself is `async def`. The second route took 1.52 s, so the requests ran one after another. The route is a `def`, but its `async def` dependency blocked the loop. Each function follows its own rule. The label on the route does not change the rule for the dependencies it uses.

More: [Concurrency and async / await](https://fastapi.tiangolo.com/async/), the parts called "Dependencies" and "Sub-dependencies", and [Dependencies - First Steps](https://fastapi.tiangolo.com/tutorial/dependencies/), the part called "To async or not to async".

## run_in_threadpool and asyncify

Sometimes an `async def` route needs `await` for one thing and a blocking library for another. You do not have to give up either. You can send the blocking call to the worker threads yourself.

```python
from fastapi.concurrency import run_in_threadpool


@app.get("/lookup")
async def lookup():
    found = await run_in_threadpool(slow_lookup)  # runs in a worker thread
    return {"found": found}
```

`run_in_threadpool` passes your arguments on, including keyword arguments. It is one of the two ways to fix the first route in the hands-on task.

Two other tools do the same job.

- `anyio.to_thread.run_sync(slow_lookup)` is the AnyIO call underneath.
- `asyncer.asyncify` comes from Asyncer, a small library by the author of FastAPI. The async docs page links to it. You write `await asyncify(slow_lookup)()`. It is a separate install, and this site does not use it.

We measured all three with 2 requests at once and a 1 s blocking function. Each batch took about 1.0 s, so they all overlapped. We used `asyncer` 0.0.18 for that check. `fastapi.concurrency.run_in_threadpool` is the same function object as the one in `starlette.concurrency`.

All three take a thread from the same pool as `def` routes. If a whole route is just one blocking call, a plain `def` is shorter and does the same. Use `run_in_threadpool` when the route really needs both worlds.

More: [Concurrency and async / await](https://fastapi.tiangolo.com/async/), the part called "Write your own async code".

## Which one to pick

The docs page gives a short rule. Follow the first line that fits.

| Your route... | Write it as |
| --- | --- |
| calls a library that you `await` | `async def` |
| calls a library that blocks (most database drivers, a sync HTTP client, file work) | `def` |
| does not wait for anything outside the process | `async def` |
| needs both, and you cannot split it | `async def`, with the blocking call in `run_in_threadpool` |
| you do not know | `def` |

Why is `def` the safe default? Compare the worst cases. A blocking call in a `def` route costs one thread, and the pool holds 40. A blocking call in an `async def` route costs every request on the server. When you are unsure, choose the mistake that costs less.

The third row has a small note from the docs. For a route that only does quick work in memory, `async def` is a little better, because it skips the thread hand-off. A `def` there is not a bug, though.

The point to take away is this. You do not need to make everything async. You need each blocking call to run somewhere it cannot hurt: in a `def` route, or in a worker thread.

More: [Concurrency and async / await](https://fastapi.tiangolo.com/async/), the part called "In a hurry?".

## How this site does it

Read `app/routes/*.py` and `app/main.py` and you will find both kinds, used for the reasons above.

| Where | Kind | What it does |
| --- | --- | --- |
| `home` and `api_progress` in `app/main.py`; the quiz, review and check routes; `history` and `reveal` in the tutor routes; `get_deeper` | `def` | read and write the store |
| `get_store` and `get_user_id` in `app/deps.py` | `def` dependencies | open the store and find the user |
| `post_deeper` in `app/routes/deeper.py` | `async def` | `await grade_answer(...)`, which asks the model 3 times at once, then saves the grade |
| `chat` in `app/routes/tutor.py` | `async def` | the tutor's streaming (SSE) route: `async with ... run_stream(...)` and `async for` over the reply |
| `lesson_page`, `api_lessons`, `licenses`, `healthz` in `app/main.py`, and the trace routes | `async def` | quick work from memory |

The store is plain sync code. It talks to SQLite, or to Postgres through the sync `psycopg` driver when `DATABASE_URL` is set. That is why the routes that mostly use the store are `def`: the blocking calls run in worker threads, as the lesson says they should.

The two `async def` routes that really wait are the ones that call the model. Waiting on a model is what `await` is for. The tutor route is an `async def` generator that yields server-sent events as it goes. While it waits for the model, the loop is free to serve other requests.

Now the honest part. Those two `async def` routes also call the sync store directly. We wrapped the store methods in a probe that asks `asyncio.get_running_loop()`, and ran the real routes with a stub in place of the model. The result:

- In `chat`, the store calls `attempts_for`, `events_for`, `chat_history` and `add_chat` ran **on the event loop**.
- In `post_deeper`, `grades_for` and `add_grade` ran **on the event loop**.
- In the `def` routes, the same store calls ran in worker threads.
- `get_store` and `get_user_id` ran in worker threads for all of them, even under the `async def` routes.

So the rule of this lesson is bent in two places. We left it that way because each call is a short query on a local SQLite file, so the loop is held for a very short time. We did not measure the Postgres setup. There, the same calls would be network round trips on the loop, and that is where the rule would start to hurt. The fixes would be `await run_in_threadpool(store.attempts_for, ...)` or an async driver.

One more detail ties back to threads. `app/store.py` opens its SQLite connection with `check_same_thread=False`. In a scratch run we put a `def` dependency with `yield`, a `def` sub-dependency and a `def` route on one app, and recorded which worker thread ran each. With one request at a time, the setup and the route ran on the same thread in 90 of 90 requests, because AnyIO reuses the thread that has just become free. With three requests at once, the setup and the route shared a thread in only 26 and 38 of 90 requests (two runs), and the closing step shared the route's thread in 57 or 58 of 90. With ten at once, it was 5 or 11 of 90. So under load, a connection opened in one worker thread is often used, and closed, in another, and this setting allows that. We read this as the reason for the setting. The code does not say so itself.

More: the code in `app/main.py`, `app/deps.py`, `app/store.py`, and `app/routes/`.

Sources (FastAPI 0.143.0, MIT licence, © 2018 Sebastián Ramírez; adapted and rewritten): [Concurrency and async / await](https://fastapi.tiangolo.com/async/), [Dependencies - First Steps](https://fastapi.tiangolo.com/tutorial/dependencies/). This site is not affiliated with FastAPI.
