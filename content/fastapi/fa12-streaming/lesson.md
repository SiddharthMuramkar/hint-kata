---
id: fa12-streaming
track: fastapi
title: "Streaming: SSE and JSON Lines, deploy notes"
minutes: 35
pins:
  fastapi: "0.143.0"
sources:
  - fastapi-tutorial-server-sent-events
  - fastapi-tutorial-stream-json-lines
  - fastapi-deployment-concepts
---

Most routes answer once: the work is done, the route returns, FastAPI sends one response. Some jobs are different. An AI model writes its reply word by word. A long job has progress to report. A log keeps growing. For these you want the client to see each piece as soon as it exists, and not wait for the last one.

One sentence is the whole mental model: **a streaming route uses `yield` instead of `return`, and each yielded item is sent to the client as soon as it is produced, written in a format that lets the client cut the stream back into items.**

FastAPI has two formats built in. JSON Lines is the plain one: one JSON object per line. Server-Sent Events (SSE) adds named events, ids and keep-alive messages. This lesson shows both, shows what happens when a stream breaks, reads the stream the way a test does, looks at the real tutor route of this site, and ends with deploy notes. FastAPI added JSON Lines streaming in 0.134.0 and SSE in 0.135.0, so both are in the 0.143.0 we pin.

Where the lesson says "we ran" or "we saw", it is an observation from 2026-10-15 (FastAPI 0.143.0, Python 3.13, uvicorn on localhost, macOS). Where it says "we read", we looked at code or a page and did not run it.

## What a stream is

A normal response is built in one piece. Streaming means your app starts sending before the whole answer exists. It sends item 1 while it is still working on item 2. The client can start using item 1 straight away. The stream can even have no end, like a live log.

The docs page draws this as a short back-and-forth between the app and the client: produce, send, produce, send, while the client processes what has already arrived. The key point is the order. The app does not collect everything first.

We measured it on a real server. A route yielded three events, with `await asyncio.sleep(0.5)` before each. The client saw them at 0.56 s, 1.06 s and 1.56 s after it asked. With a normal response, all three would have come together at the end.

More: [Stream JSON Lines](https://fastapi.tiangolo.com/tutorial/stream-json-lines/), the part called "What is a Stream?".

## JSON Lines

JSON Lines is a way to write many JSON objects in one body. You write one object per line. There are no commas between them and no `[` and `]` around them.

```text
{"n":1,"text":"read"}
{"n":2,"text":"quiz"}
{"n":3,"text":"think"}
```

A JSON array needs its closing `]` before a parser can accept it. A JSON Lines body can be read line by line, and every complete line is already a valid JSON object. That is why it suits a stream. The content type is `application/jsonl`, and not `application/json`.

A JSON object cannot contain a raw newline, because a newline ends the line. A newline inside text is written as the two characters `\n`, which is normal JSON. FastAPI does this for you. We yielded a step whose text was `"think\nhard"` and the line on the wire contained a backslash and an `n`, so it stayed one line.

More: [Stream JSON Lines](https://fastapi.tiangolo.com/tutorial/stream-json-lines/), the part called "JSON Lines".

## Streaming JSON Lines with yield

To make a JSON Lines route, write a route that yields. You do not need a special response class.

```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Step(BaseModel):
    n: int
    text: str


STEPS = [Step(n=1, text="read"), Step(n=2, text="quiz"), Step(n=3, text="think")]


@app.get("/steps/lines")
async def lines() -> AsyncIterable[Step]:
    for step in STEPS:
        yield step
```

The return type `AsyncIterable[Step]` says "this route produces many `Step` objects". The docs say FastAPI then uses it to validate each item, to document it in OpenAPI, to filter it and to serialize it with Pydantic. Without a return type, FastAPI still streams. It converts each item with `jsonable_encoder`, and Pydantic does less of the work.

We looked at the wire. With the return type, the first line was `{"n":1,"text":"read"}` with no spaces. Without it, the same step was `{"n": 1, "text": "read"}` with spaces. Both are valid JSON. The lesson is that a test must parse each line, and never compare raw text.

A plain `def` route can yield too. Its return type is then `Iterable[Step]`, and FastAPI runs it so that the event loop is not blocked. We got the same body from the `def` version.

More: [Stream JSON Lines](https://fastapi.tiangolo.com/tutorial/stream-json-lines/), the part called "Stream JSON Lines with FastAPI".

## Server-Sent Events

SSE sends text, too. It is a standard that browsers understand: the docs name the `EventSource` API as the browser's native client. Each event is a small block of lines. A blank line ends the block. Each line is `field: value`, and the fields are `data`, `event`, `id` and `retry`. A line that starts with a colon is a comment, and clients ignore it.

```text
event: step
data: {"n":1,"text":"read"}
id: 1

event: done
data: [DONE]

```

You make an SSE route in two steps. Yield from the route, and set `response_class=EventSourceResponse`. The class lives in `fastapi.sse`.

```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel

app = FastAPI()


class Step(BaseModel):
    n: int
    text: str


STEPS = [Step(n=1, text="read"), Step(n=2, text="quiz"), Step(n=3, text="think")]


@app.get("/steps/events", response_class=EventSourceResponse)
async def events() -> AsyncIterable[Step]:
    for step in STEPS:
        yield step
```

Each yielded item is encoded as JSON and put in a `data:` line. The content type becomes `text/event-stream`. We saw that, and we also saw that FastAPI adds two headers for you: `cache-control: no-cache` and `x-accel-buffering: no`.

Do not forget `response_class`. We left it off on a route that yielded `ServerSentEvent` objects. FastAPI did not complain. It streamed JSON Lines, and every line was the whole `ServerSentEvent` object turned into JSON, with keys like `data`, `event` and `retry`. Status 200, wrong format. The page says SSE needs the response class.

SSE works with any HTTP method, not only `GET`. The docs show a `POST` route that streams the words of a prompt. This site's tutor route is a `POST`.

More: [Server-Sent Events (SSE)](https://fastapi.tiangolo.com/tutorial/server-sent-events/), the parts called "What are Server-Sent Events?" and "Stream SSE with FastAPI".

## Named events with ServerSentEvent

Plain items only fill the `data` field. To name an event or give it an id, yield a `ServerSentEvent` from `fastapi.sse`.

```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent

app = FastAPI()


@app.get("/count", response_class=EventSourceResponse)
async def count() -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(comment="counting starts")
    for n in (1, 2, 3):
        yield ServerSentEvent(data={"n": n}, event="step", id=str(n))
    yield ServerSentEvent(raw_data="[DONE]", event="done")
```

On the wire, we saw this:

```text
: counting starts

event: step
data: {"n": 1}
id: 1

event: step
data: {"n": 2}
id: 2

event: step
data: {"n": 3}
id: 3

event: done
data: [DONE]

```

The client can now react to each kind of event on its own. A page can append text for `step`, and close a spinner for `done`.

Three details are easy to miss. We checked each one.

- **`data` is always JSON.** `ServerSentEvent(data="[DONE]")` gives `data: "[DONE]"`, with the quotes. If you need the text with no JSON encoding, for a log line or for a marker such as `[DONE]`, use `raw_data`. You may set one of them, not both. We set both, and the test client got an empty body.
- **A multi-line `raw_data` becomes several `data:` lines.** We sent `"line one\nline two"` and got one `data:` line per line. A client has to join them again. A JSON `data` never has this problem, because it is always one line.
- **A wrong field name is ignored, not rejected.** We wrote `name="step"` instead of `event="step"`. There was no error. The event just had no name. Yielding a plain dict with an `"event"` key does not work either: the whole dict ended up inside `data`.

The `id` and `retry` fields are for reconnecting. A browser that loses its connection reconnects, and it sends the last `id` it saw in a header called `Last-Event-ID`. You can read that header in your route and continue from there.

```python
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import FastAPI, Header
from fastapi.sse import EventSourceResponse, ServerSentEvent

app = FastAPI()


@app.get("/resume", response_class=EventSourceResponse)
async def resume(
    last_event_id: Annotated[int | None, Header()] = None,
) -> AsyncIterable[ServerSentEvent]:
    start = 0 if last_event_id is None else last_event_id + 1
    for n in (1, 2, 3):
        if n >= start:
            yield ServerSentEvent(data={"n": n}, id=str(n))
```

We called the same kind of route with `Last-Event-ID: 1` and got only the events after it. This is the docs' resume example in our words. `retry` is also a reconnect hint, and its exact meaning is in the HTML specification, not on the page we used. We only checked how it is written (`retry: 3000`). We did not test a browser reconnecting.

One more thing FastAPI does without being asked. If the stream is quiet for 15 seconds, it sends a comment line, `: ping`. Some proxies close a connection that has been silent for too long, and the ping keeps it open. We tested this: a route sent an event, waited 17 s, and sent another. The client saw the first event at 0 s, `: ping` at 15 s and the second event at 17 s.

More: [Server-Sent Events (SSE)](https://fastapi.tiangolo.com/tutorial/server-sent-events/), the parts called "ServerSentEvent", "Raw Data", "Resuming with Last-Event-ID" and "Technical Details".

## SSE or JSON Lines

Both stream. The choice is about who reads the stream and what it needs.

| You need | Pick |
| --- | --- |
| a browser to read it with its built-in `EventSource` | SSE |
| several kinds of message on one stream (tokens, progress, errors, a final result) | SSE, with named events |
| a client to resume after a drop | SSE, with `id` and `Last-Event-ID` |
| a proxy to be told not to hold the stream back | SSE (the two headers and the ping come for free) |
| a simple stream of one kind of record for a script, a log tool or another service | JSON Lines |

The cost of SSE is a little more format to learn. The cost of JSON Lines is that every message is one shape, and you invent your own conventions for the rest. Neither is better. If you are unsure, SSE gives you more room.

More: [Server-Sent Events (SSE)](https://fastapi.tiangolo.com/tutorial/server-sent-events/) and [Stream JSON Lines](https://fastapi.tiangolo.com/tutorial/stream-json-lines/).

## When a stream breaks

Here is the part that surprises people. The status code is sent first, before the first item. After that it is too late to change it. So if your route fails halfway, the client has already been told "200 OK".

We tested this against a real server, with a route that yielded one item and then raised `RuntimeError`.

- **JSON Lines:** the status was 200, the client received the first line, and then the connection ended. The client library (`httpx`) raised `RemoteProtocolError`, with the message "peer closed connection without sending complete message body".
- **SSE:** the same. The status was 200 and the stream ended in an error. In our run, the first event did not arrive either, because the error came straight after it. Do not count on a partial result.
- **A bad item in a typed route:** we yielded a dict that did not match `Step`. FastAPI checks each item as it sends it, so this is a failure in the middle of the stream, too. The first line arrived, then the same `RemoteProtocolError`.

FastAPI does not turn any of these into a 500 response, and it does not send an `error` event for you. Your route has to do it. The pattern is to catch the exception inside the generator and yield an event the client understands. This site's tutor route does exactly this, as you will see below.

```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent

app = FastAPI()


def do_risky_work(n: int) -> None:
    if n == 2:
        raise RuntimeError("the second step fails")


@app.get("/safe", response_class=EventSourceResponse)
async def safe() -> AsyncIterable[ServerSentEvent]:
    try:
        for n in (1, 2, 3):
            yield ServerSentEvent(data={"n": n}, event="step")
            do_risky_work(n)
    except Exception:
        yield ServerSentEvent(data="The job failed.", event="error")
```

We ran a route of this shape. The client got its `step` event, then the `error` event, and a clean end of the stream. With JSON Lines there are no event names, so you would agree on a convention yourself, such as one line that holds an `"error"` key.

A second case is the client leaving. We opened a stream that sent ten events, 0.2 s apart, and closed the connection after two. In the route, the generator was cancelled at its `await`, with `CancelledError`. A `finally` block ran. The code after the last `yield` did **not** run. So cleanup belongs in `finally`, and anything that must happen only at a normal end needs to be written with that in mind.

The last case is the event loop, which you met in lesson FA7. An `async def` generator runs on the loop. If it calls `time.sleep(0.5)` between yields, it blocks the loop, just like a blocking call in an `async def` route. We ran three events with a blocking sleep of 0.5 s each, and called a quick `/ping` route every 0.2 s next to it. In one run, two pings took 0.81 s and 0.30 s, instead of about 0.001 s. The stream's own response did not even start until 0.5 s, and its three events came together at about 1.5 s. With the same sleep inside a plain `def` generator, the pings stayed at 0.001 s and the events arrived 0.5 s apart. So a stream follows the FA7 rule: wait with `await`, or use a plain `def` generator for blocking work.

More: the page [Server-Sent Events (SSE)](https://fastapi.tiangolo.com/tutorial/server-sent-events/) describes the non-async version. The failure cases come from our own runs.

## Reading a stream in a test

A test has two jobs here: check the format, and check the content. For both, parse the stream. Do not compare raw text.

Here is one complete test file. It has the two routes, a small SSE parser, and a test for each stream. For JSON Lines, you split the body into lines and run `json.loads` on each one. For SSE, you split the body at blank lines into blocks, then read the `field: value` lines of each block, and skip comment lines, which start with a colon.

```python
import json
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent
from fastapi.testclient import TestClient
from pydantic import BaseModel

app = FastAPI()


class Step(BaseModel):
    n: int
    text: str


STEPS = [Step(n=1, text="read"), Step(n=2, text="quiz"), Step(n=3, text="think")]


@app.get("/steps/lines")
async def lines() -> AsyncIterable[Step]:
    for step in STEPS:
        yield step


@app.get("/count", response_class=EventSourceResponse)
async def count() -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(comment="counting starts")
    for n in (1, 2, 3):
        yield ServerSentEvent(data={"n": n}, event="step", id=str(n))
    yield ServerSentEvent(raw_data="[DONE]", event="done")


client = TestClient(app)


def parse_sse(text: str) -> list[dict[str, str]]:
    events = []
    for block in text.split("\n\n"):
        fields = {}
        for line in block.splitlines():
            if line and not line.startswith(":"):
                key, _, value = line.partition(": ")
                fields[key] = value
        if fields:
            events.append(fields)
    return events


def test_lines() -> None:
    response = client.get("/steps/lines")
    assert response.headers["content-type"].startswith("application/jsonl")
    items = [json.loads(line) for line in response.text.splitlines()]
    assert [item["n"] for item in items] == [1, 2, 3]


def test_events() -> None:
    events = parse_sse(client.get("/count").text)
    assert [e["event"] for e in events] == ["step", "step", "step", "done"]
    assert json.loads(events[0]["data"]) == {"n": 1}
    assert events[-1]["data"] == "[DONE]"  # raw_data: no quotes
```

We ran this file, and both tests pass.

This little parser keeps only one `data:` line per event. That is enough here, because `data` is JSON and so is always one line. A parser for any SSE source would join several `data:` lines with a newline.

`TestClient` gives you the whole body once the stream has ended. That is fine for checking format and content. It does not show you the timing, so we measured that above against a real uvicorn server.

The hands-on task for this lesson uses these two ideas. You fix one JSON Lines route and one SSE route, and the hidden tests parse the streams like this.

## How this site streams the tutor

Open `app/routes/tutor.py` and look at `chat`. It is the SSE route of the tutor. Its pieces match this lesson.

- **`@router.post(..., response_class=EventSourceResponse)`.** An SSE route on `POST`, because the learner's message is sent in a JSON body. The return type is `AsyncIterable[ServerSentEvent]`.
- **Named events.** The route yields `token` events while the model writes (only when the hint level allows it), then `ceiling`, `html` and `citations`, and `error` when something goes wrong. The page's JavaScript, in `app/static/js/tutor.js`, reads each block and does a different thing for each event name.
- **A catch inside the generator.** The model call sits in `try`. On an exception the route logs it, yields `ServerSentEvent(event="error", ...)` and returns. That is the pattern from the section on broken streams.
- **`async def`.** The route awaits the model with `run_stream` and loops over the reply with `async for`. Waiting on a model is what `await` is for, as FA7 explained.
- **Saving after the last yield.** The two `store.add_chat(...)` calls come after the `citations` event. By the cancellation result above, we read that a learner who closes the tab before that point would not get this turn saved. We did not run this on the real route.

The JavaScript reads the stream with `fetch` and a reader, and not with `EventSource`, because the request is a `POST` with a body. It cuts the text at blank lines and reads the `event:` and `data:` lines. It takes only one `data:` line per event and ignores `: ping` lines. That is safe because every `data` here is JSON, so it is always one line.

More: the code in `app/routes/tutor.py` and `app/static/js/tutor.js`.

## Deploy notes

A stream is a request that lasts a long time. That changes how some of the deploy concepts feel. The [Deployments Concepts](https://fastapi.tiangolo.com/deployment/concepts/) page lists six: HTTPS, running on startup, restarts, replication, memory, and previous steps. Here is how each one meets a stream.

| Concept (from the docs page) | What it means for a stream |
| --- | --- |
| HTTPS | A separate component, the TLS termination proxy, normally sits in front of your app. A stream passes through it. The two headers and the 15-second ping FastAPI sets exist so that proxies like Nginx do not buffer the stream or close it while it is quiet. We did not run a proxy. |
| Running on startup | A separate program, such as Docker or systemd, starts your server. Nothing special for streams. |
| Restarts | The process can crash or be restarted. The open stream dies with it, and the client sees a broken stream like the one we saw above. Design the client to reconnect. With SSE, `id` and `Last-Event-ID` let it continue. That is our reasoning, we did not restart a server mid-stream. |
| Replication (workers) | Several worker processes can serve the same app. A reconnecting client may land on a different one. |
| Memory | Processes do not share memory. A list of recent events kept in a Python variable exists in one worker only. |
| Previous steps | Things like database migrations should run once, not once per worker. Not specific to streams. |

The memory row bites if you try to support `Last-Event-ID`. Say you keep the last 100 events in a list so that a client can resume. The client reconnects to another worker, and that worker's list is empty. Or you redeploy, and every list is gone. To resume reliably, keep the events somewhere that all workers can read and that survives a restart, such as a database, and take the `id` from it.

Time limits matter too. This site runs on Vercel, and `vercel.json` sets `maxDuration` to 300 seconds. The runbook `docs/runbooks/vercel.md` says streaming responses stop at 300 s on the Hobby plan. We did not test what happens at that limit. A stream that can last longer must treat "the stream ended" as normal and reconnect. The same runbook says SQLite on Vercel lives in `/tmp` and instances do not share it, which is the memory row of the table, seen in a real project.

The point to take away is this. A stream is easy to write and a little harder to run. Write the route with the reconnect in mind: ids that come from something durable, an `error` event for failures, cleanup in `finally`, and a client that expects the stream to end sometimes.

More: [Deployments Concepts](https://fastapi.tiangolo.com/deployment/concepts/), and `docs/runbooks/vercel.md` and `vercel.json` in this repo.

Sources (FastAPI 0.143.0, MIT licence, © 2018 Sebastián Ramírez; adapted and rewritten): [Server-Sent Events (SSE)](https://fastapi.tiangolo.com/tutorial/server-sent-events/), [Stream JSON Lines](https://fastapi.tiangolo.com/tutorial/stream-json-lines/), [Deployments Concepts](https://fastapi.tiangolo.com/deployment/concepts/). The tutor route and Vercel parts come from this site's own code and runbook, and from our own runs. This site is not affiliated with FastAPI.
