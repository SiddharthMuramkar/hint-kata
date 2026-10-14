# Task: serve an agent over Server-Sent Events

You will finish a small FastAPI app. It has one route, `POST /chat`. The route runs an agent on the message it gets, and it sends the reply back as a stream of events.

Open `sse_app.py` in your workspace. `make_agent(model)` is already written. It takes a model, so the tests can hand in a fake one. The route is inside `make_app(agent)`. It has three TODO comments.

1. **Make it an SSE route** (TODO 1). Add the argument to the route decorator that tells FastAPI to send `text/event-stream`. The starter has none, so FastAPI streams JSON lines instead.
2. **Stream the text as `token` events** (TODO 2).
   - Open the run with `agent.run_stream(body.message)` (an async context manager).
   - Loop over `result.stream_text(...)`. Each event must hold only the **new** text of a chunk, not the text so far.
   - You need one item per chunk. A scripted model is so fast that the default groups its chunks into one item. Read the section "Running the agent inside the generator" to find the two options you need.
   - For each piece, add it to `parts` and `yield` a `ServerSentEvent` named `"token"` with the piece as its data.
3. **End with a `done` event** (TODO 3). After the loop, `yield` one `ServerSentEvent` named `"done"`. Its data is the full text: all the pieces joined.

Delete the placeholder `yield` line when your own lines are in. The route is an async generator, so do not use `return` to send events.

## How the check works

The hidden tests build the app with `make_app(make_agent(FunctionModel(...)))`. The fake model streams a scripted answer in four chunks, and `ALLOW_MODEL_REQUESTS` is `False`, so no API key is needed. The tests post to `/chat` with `TestClient` and group the lines they get into events. They check that:

- the response has the `text/event-stream` content type.
- there are at least two `token` events, and joined together they are exactly the scripted text (new text only, no repeats).
- there is exactly one `done` event, it is the last event, and its data is the full text.
- the message in the request body is what the agent runs on.

`TestClient` runs the whole app before it gives the response back, so the tests check what arrived, not when. The section "Testing a stream" explains why.

Press **Check my work** when you are ready. If a test fails, read its message and the lesson sections "Sending events with FastAPI" and "Running the agent inside the generator".
