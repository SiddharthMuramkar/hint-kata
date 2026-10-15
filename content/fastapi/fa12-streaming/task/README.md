# Task: one JSON Lines stream and one SSE stream

Open `workspace/fa12-streaming/api.py`. It has a list of three `Step` objects and two routes.
Both routes already answer with status 200, and both are wrong in a way that only shows when you
look at the bytes.

Do not change `Step` or `STEPS`.

## 1. `GET /steps/lines` is not a stream

The route builds the whole list and returns it. The client gets one JSON array with the content
type `application/json`. Nothing is sent before the whole list is ready.

Make it a JSON Lines stream. Use `yield` to send one `Step` at a time, and declare the return type
as `AsyncIterable[Step]`. The client should get three lines, one JSON object each, with the content
type `application/jsonl`.

## 2. `GET /steps/events` sends nameless events

This is an SSE route, but its events have no name and no id, and the last one is the JSON string
`"done"`, with quotes. Fix it so that:

- each step is an event named `step`, with `id` set to the step number as text (`"1"`, `"2"`,
  `"3"`) and the step in `data`;
- after the three steps comes one event named `done` whose `data:` line is exactly `[DONE]`, with
  no quotes.

You need `ServerSentEvent` from `fastapi.sse`. Ask yourself which of its two data fields does not
encode the value as JSON.

## Check your work

The hidden tests call both routes with FastAPI's `TestClient` and parse the bodies. For JSON Lines
they split the text into lines and run `json.loads` on each one. For SSE they cut the text at blank
lines into events and read each `field: value` line. They do not compare raw text, because the
spaces inside the JSON may differ.

If a test fails, read its message. It shows the content type, the event names or the data line that
the test found.
