---
id: pa7-serving-over-sse
track: pydantic-ai
title: "Serving an agent from FastAPI over SSE"
minutes: 30
pins:
  pydantic-ai: "2.56.0"
  fastapi: "0.143.0"
sources:
  - fastapi-tutorial-server-sent-events
  - pydantic-ai-core-concepts-agent
  - pydantic-ai-integrations-ui-overview
  - pydantic-ai-guides-testing
  - fastapi-tutorial-testing
---

An agent can take many seconds to write an answer. A normal web response cannot show half of it. The server finishes first, then sends everything. In this lesson you send the reply while it is still being written. You use FastAPI's built-in Server-Sent Events (SSE), you read the stream with `fetch`, you test it without an API key, and you see how this site's tutor does it. We ran the examples on Pydantic AI 2.56.0 and FastAPI 0.143.0. Where we only watched something happen, the text says "observed". Where a point comes from the docs and we did not run it, the text says so.

## One request, many events

A normal request gets one response: a status code, headers, a body, and it is over. A streamed reply keeps the response open. The server sends the status and the headers first. Then it sends pieces of the body over time. At the end it closes the response. That is one request and many events.

Two things follow from this.

- **The status code goes out first.** If the model fails halfway, the server cannot change the `200` into a `500`. It has to tell the client inside the body. Observed: we made a route fail before it sent anything. The client still got `200` and `text/event-stream`, and then the connection was cut.
- **The client must read the body in pieces.** It cannot wait for the end, or the stream is pointless.

SSE is the format for this. It is plain text. Each event is a block of lines that ends with a blank line. A line has a field name, a colon and a value. The two fields you will use most are `event` (the name) and `data` (the payload):

```text
event: token
data: "Hello "

event: token
data: "world"

```

The blank line is what ends an event. The [FastAPI SSE page](https://fastapi.tiangolo.com/tutorial/server-sent-events/#what-are-server-sent-events) shows the same format.

## Sending events with FastAPI

FastAPI 0.143.0 has SSE built in. The docs say it was added in 0.135.0. You need three things:

```python
from collections.abc import AsyncIterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

app = FastAPI()


class ChatIn(BaseModel):
    message: str


@app.post("/chat", response_class=EventSourceResponse)
async def chat(body: ChatIn) -> AsyncIterable[ServerSentEvent]:
    yield ServerSentEvent(event="token", data="Hello ")
    yield ServerSentEvent(event="token", data="world")
    yield ServerSentEvent(event="done", data="Hello world")
```

- `response_class=EventSourceResponse` tells FastAPI to send `text/event-stream`.
- The endpoint is a **generator**: it uses `yield`. Each `yield` is one event. The docs add that a plain `def` generator works too, and that FastAPI runs it so the event loop is not blocked.
- `ServerSentEvent(event=..., data=...)` sets the name and the payload.

Nothing ties SSE to `GET` on the server. A `POST` route with a JSON body works, and the docs have a [`POST` example](https://fastapi.tiangolo.com/tutorial/server-sent-events/#sse-with-post). That matters for chat, because the message goes in the body.

Three details we checked.

- **`data` is always JSON-encoded, even a string.** Observed: `data="Hello "` goes out as `data: "Hello "`, with the quotes. A newline inside the string goes out as `\n` inside the quotes, so the value stays on one line. The client must `JSON.parse` it. You can also pass a dict, a list or a Pydantic model as `data`.
- **`raw_data` skips the encoding.** Use it for text that is already formatted. You cannot set `data` and `raw_data` on the same event. Observed: a `raw_data` string with a line break becomes two `data:` lines.
- **Forget `response_class` and you do not get SSE.** Observed: a generator endpoint without it still streams, but as JSON Lines. The `Content-Type` was `application/jsonl`, and each `ServerSentEvent` was dumped as one JSON object with all its fields (`{"data": "hi", "raw_data": null, "event": "token", ...}`). Nothing fails. The stream just has the wrong shape.

Put `-> AsyncIterable[ServerSentEvent]` on the endpoint so the code says what the route yields.

## Running the agent inside the generator

Lesson PA4 showed `agent.run_stream()` and `stream_text()`. Here the new part is small: you `yield` from inside the loop.

```python
@app.post("/chat", response_class=EventSourceResponse)
async def chat(body: ChatIn) -> AsyncIterable[ServerSentEvent]:
    parts: list[str] = []
    async with agent.run_stream(body.message) as result:
        async for delta in result.stream_text(delta=True, debounce_by=None):
            parts.append(delta)
            yield ServerSentEvent(event="token", data=delta)
    yield ServerSentEvent(event="done", data="".join(parts))
```

FastAPI pulls one event at a time from the generator and writes it out. The generator does not wait for the browser to read the event. The agent run stays open until the loop ends. Then the generator sends a last event and ends, and FastAPI closes the response. If the browser leaves, the generator is cancelled.

On a scripted model, this is what the client read (observed):

```text
event: token
data: "Tea "

event: token
data: "costs "

event: token
data: "2.75 "

event: token
data: "with tax."

event: done
data: "Tea costs 2.75 with tax."

```

Notes on the choices.

- **`delta=True` is the point.** The page appends each `token` to the reply box, so each event must hold only the new text. Observed: with the default `stream_text()`, the events were `"Tea "`, `"Tea costs "`, `"Tea costs 2.75 "` and so on. A page that appends them shows the text again and again.
- **`debounce_by`** groups chunks that arrive within 0.1 seconds into one item. That is fine for a real model, and it saves events. A scripted model is so fast that the default gave one `token` event with the whole text (observed). Pass `debounce_by=None` in tests, so each scripted chunk is its own event.
- **`done` is our own name.** SSE and the browser give it no special meaning. It is a convention: "here is the full text, you can stop". The site's tutor route has no `done` event. It just ends.
- **Code after the loop runs only if the client stays.** Observed: when the client closed the connection after the first event, the generator received a `CancelledError`. The line after the loop never ran. A save placed there is skipped when the reader leaves. Decide if that is what you want.

## Named events for everything else

The `event` name lets one stream carry several kinds of message. The client picks what to do by name. This site's tutor uses `token` for text pieces, `html` for the final reply, `citations` for a list, and `error` for failures. Because `data` is JSON, a list or a dict works (observed: a dict goes out as `data: {"text": "hi", "n": 1}`).

Errors need a plan. The status is already `200`, so you send the failure as an event:

```python
    parts: list[str] = []
    try:
        async with agent.run_stream(body.message) as result:
            async for delta in result.stream_text(delta=True, debounce_by=None):
                parts.append(delta)
                yield ServerSentEvent(event="token", data=delta)
    except Exception:
        log.exception("agent run failed")  # the details stay on the server
        yield ServerSentEvent(event="error", data="The model failed, please retry.")
        return
```

Observed, on a live server, when a model fails after two chunks:

- **With the `try`/`except`:** the client got two `token` events, then one `error` event. The status was `200`.
- **Without it:** the client got `200` and then a cut connection. `httpx` raised `RemoteProtocolError`. The `tutor.js` loop, run in Node 24, behaved differently. After the two `token` events it simply ended with `done: true`, as if the reply were finished (5 runs out of 5). The page cannot tell a cut stream from a finished one. No `error` event arrives, because FastAPI does not make one for you, and that is the case for sending one yourself. (When the route failed before it sent any event, `reader.read()` rejected with a `TypeError` instead. We did not test a real browser.)

Mistakes in the request itself are different. FastAPI checks the body before the stream starts, so a bad body is a normal answer. Observed: a `422` with `application/json`. The browser code must look at the status before it starts reading events.

## Keep-alive pings and headers

You write none of this. FastAPI does it for you. The [docs list three things](https://fastapi.tiangolo.com/tutorial/server-sent-events/#technical-details), and we saw all of them.

- **`Cache-Control: no-cache`** so nothing stores the stream. Observed in the response headers.
- **`X-Accel-Buffering: no`** so proxies such as Nginx do not hold the events back. Observed.
- **A keep-alive line, `: ping`.** After 15 seconds with nothing sent, FastAPI writes this comment line into the stream. Its job, per the docs, is to stop some proxies from dropping a connection that looks idle. That matters for agents, because a model may think for a while before the first token.

The response also carried `Content-Type: text/event-stream; charset=utf-8` (observed).

We saw the pings by turning the interval down to 0.25 seconds in a scratch run. That setting is a private name in FastAPI, so do not copy it. A ping is a block with a colon at the start and no `data:` line:

```text
: ping

```

A reader must skip blocks that have no `data:`. The next section shows where the site's reader does it.

## Reading the stream in the browser

The browser has `EventSource`, an API made for SSE. It reconnects by itself. But `new EventSource(url)` takes a URL and one option (`withCredentials`), so it always sends a `GET` with no body ([MDN](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) describes it; this point is not in our sources). A chat message needs a `POST` body. So the page uses `fetch` and reads the response body as a stream.

The reader is in `app/static/js/tutor.js`. The file is over 100 lines long, because it also draws chat bubbles, loads the history and handles the reveal button. The streaming core is the `try ... finally` block inside the submit handler. It is about 35 lines. This is its heart:

```javascript
const res = await fetch(base, {
  method: "POST",
  headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
  body: JSON.stringify({ message, active_item: root.dataset.activeItem || null }),
});
if (!res.ok || !res.body) throw new Error("HTTP " + res.status);
const reader = res.body.getReader();
const decoder = new TextDecoder();
let buffer = "";
for (;;) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  let cut;
  while ((cut = buffer.indexOf("\n\n")) !== -1) {
    const block = buffer.slice(0, cut);
    buffer = buffer.slice(cut + 2);
    let type = "message", data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) type = line.slice(7);
      else if (line.startsWith("data: ")) data += line.slice(6);
    }
    if (!data) continue; // ': ping' keep-alives
    const v = JSON.parse(data);
    if (type === "token") reply.textContent += v;
    // ... one more branch for each of html, ceiling, citations and error
  }
}
```

Read it in this order.

1. **`fetch` with `POST`.** It sends the JSON body. The `Accept` header says what the page wants.
2. **`if (!res.ok ...) throw`.** A `404` or `422` comes back as a plain response, not as events. The code checks first.
3. **`getReader()`.** `reader.read()` waits for the next piece of bytes. `done` becomes `true` when the server closes the response. That is how the page knows the stream is over.
4. **`TextDecoder` with `{ stream: true }`.** A character can be split between two reads. This flag keeps the half character until the next read.
5. **The `buffer`.** One read can end in the middle of an event, or hold three events. So the code adds each read to the buffer and cuts out whole blocks at each blank line (`"\n\n"`). The rest stays for the next read.
6. **The block parser.** `event: ` sets the type (the default is `message`). `data: ` lines are joined. They are joined with no line break, which is fine here, because FastAPI JSON-encodes `data` onto one line. It would flatten a multi-line `raw_data`.
7. **`if (!data) continue`.** This skips the `: ping` blocks.
8. **`JSON.parse(data)`.** This undoes the server's JSON encoding.
9. **One branch per event name.** The tutor handles five names: `token`, `ceiling`, `html`, `citations` and `error`. A name with no branch, such as `done`, is ignored without any message.

The `catch` block shows a connection error and the `finally` block turns the send button back on.

We ran the loop above in Node 24 against a scratch server that sent pings (observed). It skipped every ping, appended the four `token` values into `"Tea costs 2.75 with tax."`, and ignored `done`.

## Testing a stream

You can test the route with no key. Give the agent a `FunctionModel` with a `stream_function`, as in lesson PA4, and set `models.ALLOW_MODEL_REQUESTS = False`. The [Pydantic AI testing guide](https://pydantic.dev/docs/ai/guides/testing/#unit-testing-with-functionmodel) explains both.

Then use FastAPI's `TestClient` ([Testing](https://fastapi.tiangolo.com/tutorial/testing/)):

```python
client = TestClient(app)
with client.stream("POST", "/chat", json={"message": "How much is tea?"}) as response:
    lines = list(response.iter_lines())  # 'event: token', 'data: "Tea "', '', ...
```

Group the lines into blocks. A blank line ends a block. Take `event:` as the name and `json.loads` the `data:` value. Skip a block that has no `data:`.

**`TestClient` buffers the whole stream.** Observed: we made the fake model wait 0.4 seconds between four chunks. The `client.stream(...)` call took about 1.6 seconds to open, and then every line was there at the same moment. `httpx.ASGITransport` did the same. So these tests check **what** arrived, such as the names, the data and the order. They cannot check **when** it arrived.

To see the timing, run a real server (for example `uvicorn`) and read it with `httpx.stream`:

```python
with httpx.stream("POST", "http://127.0.0.1:8000/chat", json={"message": "hi"}) as r:
    for line in r.iter_lines():
        print(line)
```

Observed, with the same 0.4 second gaps: the four `token` events arrived at 0.46, 0.86, 1.27 and 1.67 seconds. That is real streaming.

## Other ways to serve an agent

You do not always have to write the route. Pydantic AI has **UI adapters** that parse the request, run the agent and encode the events for a protocol your frontend already speaks. `VercelAIAdapter` speaks the Vercel AI Data Stream Protocol and `AGUIAdapter` speaks AG-UI. In FastAPI you call `VercelAIAdapter.dispatch_request(request, agent=agent)` from your endpoint. The [UI Event Streams](https://pydantic.dev/docs/ai/integrations/ui/overview/) page explains the choices. `Agent.to_web()` is different. It returns a small Starlette app with a chat page, so you can talk to an agent in a browser. The [Web Chat UI page](https://pydantic.dev/docs/ai/guides/web/) presents it as a tool for working on your agent on your own machine, and it points to the UI adapters for production. A hand-written route, like the one in this lesson, is the choice when you want to decide the events yourself.

## How the tutor route does it

The tutor on this site is the route you just built, with more rules. The code is in `app/routes/tutor.py`. We ran the real route on a local server with a scripted tutor model and a temporary database, and these points are what we saw.

1. **The route** is `POST /api/tutor/{lesson_id}`. It has `response_class=EventSourceResponse` and returns `AsyncIterable[ServerSentEvent]`. FastAPI looks up the lesson, the store and the user before the stream starts, so an unknown lesson is a plain `404`.
2. **The run** is `async with get_tutor().run_stream(...)` and `async for delta in result.stream_text(delta=True)`. The route keeps every delta in a list. It does not pass `debounce_by`.
3. **The hint ceiling gates the `token` events.** The ceiling is the highest rung of the hint ladder that the tutor may use in this turn. The server sets it. The route sends a `token` event only when `ceiling >= 4`. Below that, the server removes code blocks from the finished reply, and it can only do that once it has the whole reply. So a live token could show code that the final reply must not have. Observed: on a first turn (ceiling `L1`) the events were `ceiling`, `html`, `citations` and nothing else. After "Show me" lifted the ceiling to `L6`, four `token` events came first.
4. **The closing events.** After the loop, the route joins the deltas, applies the ceiling, drops citation markers that are not sections of the lesson, and yields `ceiling`, `html` and `citations`. The page replaces its live text with the `html`. When the tutor's RAG mode is on, the route also checks any `[src:N]` markers against the doc pieces it sent to the model in this turn, drops the unknown ones, and adds each valid one to the `citations` event with its title and URL. There is no `done` event. The end of the generator is the end of the stream.
5. **Then it saves the turn.** It writes the learner's message and the reply to the `chats` table. This code sits after the last `yield`. Observed: when the client left after the first `token`, the history had the same number of rows as before. The turn was not saved.
6. **If the run raises,** the route logs it, yields one `error` event and returns. Observed: with a model that failed after two chunks, the client got two `token` events and then `error`, with status `200`. Nothing was saved.

Compare this with your own route. The streaming part is still one `async with`, one `async for` and one `yield`. Everything else is rules about what the learner may see and what gets saved.

Sources (FastAPI 0.143.0, MIT licence, © 2018 Sebastián Ramírez; adapted and rewritten): [Server-Sent Events (SSE)](https://fastapi.tiangolo.com/tutorial/server-sent-events/) and [Testing](https://fastapi.tiangolo.com/tutorial/testing/). Sources (Pydantic AI documentation, version 2.56.0, MIT licence, © Pydantic Services Inc. 2024 to present; adapted and rewritten): [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/), [UI Event Streams](https://pydantic.dev/docs/ai/integrations/ui/overview/) and [Unit Testing](https://pydantic.dev/docs/ai/guides/testing/). The note on `Agent.to_web()` comes from two places: the Pydantic AI [Web Chat UI](https://pydantic.dev/docs/ai/guides/web/) page (the advice to use it locally) and the method's docstring in 2.56.0 (what it returns). That page is linked only. It is not one of this site's registered sources. This site is not affiliated with FastAPI or Pydantic.
