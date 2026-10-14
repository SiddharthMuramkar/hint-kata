# Task: two routes that do not play well with the event loop

Open `workspace/fa7-async-vs-def/api.py`. It has two helper functions and two routes. Both routes
return the right answer when you call them one at a time. Each one has a problem that only shows
when several requests arrive together, or when you look at the response closely.

Do not change the two helpers. They stand in for libraries you do not control:

- `slow_lookup()` is a plain function that blocks for 0.3 s, like a sync HTTP client or a sync
  database driver.
- `fetch_rate()` is an `async def` function that waits for 0.3 s with `await`, like an async HTTP
  client.

## 1. `GET /lookup` blocks the whole server

The route is `async def` and calls `slow_lookup()` straight away. That freezes the event loop for
0.3 s on every request. Three requests at once take about 0.9 s, and every other request on the
server waits too.

Fix it so that three requests at once take about 0.3 s. There are two ways, and either one passes:

- make the route a plain `def`, or
- keep `async def` and call the blocking function through `run_in_threadpool` (it is in
  `fastapi.concurrency`).

The route must still return `{"result": "found"}`.

## 2. `GET /rate` returns the wrong thing

The route is a plain `def`, and it calls `fetch_rate()` without `await`. A call to an `async def`
function only makes a coroutine, and nothing runs it. The client does not get `{"rate": 1.25}`.

Fix the route so the client gets `{"rate": 1.25}` with status 200, and so that three requests at
once still take about 0.3 s. Ask yourself which of the two keywords `await` needs.

## Check your work

The hidden tests send three requests at the same moment to each route, through an in-process
client, and measure how long the batch takes. A batch that runs one request after another takes
at least 0.9 s. A batch that overlaps takes about 0.3 s. The tests accept anything under about
0.7 s, so a slow computer is fine. They also check that each route still waits for its helper, so
removing the sleep is not a fix.

If a test fails, read its message. It says how long the batch took. Then ask: is this blocking
call running on the event loop, or in a worker thread?
