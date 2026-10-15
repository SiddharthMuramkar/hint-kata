## What changed

This adds lesson FA12, "Streaming: SSE and JSON Lines, deploy notes" (35 minutes), to the FastAPI track. The idea in one sentence: a streaming route uses `yield` instead of `return`, and each yielded item is sent to the client as soon as it is produced, in a format that lets the client cut the stream back into items.

The reading has ten short sections:

- What a stream is, and JSON Lines (one JSON object per line, `application/jsonl`).
- Streaming JSON Lines with `yield` and a return type.
- Server-Sent Events with `EventSourceResponse`, and named events with `ServerSentEvent` (`event`, `id`, `data` against `raw_data`, `Last-Event-ID` resume, the 15-second `: ping`).
- When to pick SSE or JSON Lines.
- When a stream breaks: the status is already 200, so a failure in the middle cuts the stream and the route must yield its own `error` event. A client that leaves cancels the generator.
- Reading a stream in a test, with a small SSE parser.
- How this site's tutor route (`app/routes/tutor.py`) uses the same pieces.
- Deploy notes: how the six concepts of the FastAPI deployment page (HTTPS, startup, restarts, replication, memory, previous steps) meet a long-lived stream, plus the 300 s limit in `vercel.json`.

Everything the lesson says "we ran" was run on FastAPI 0.143.0 and Python 3.13 with a real uvicorn server (arrival times of events, the broken stream after an error, the cancelled generator, the blocked event loop, the 15 s ping). Every code sample in the lesson was run too. What we only read is marked "we read": the tutor route saving its history after the last `yield`, the proxy behaviour, the restart behaviour and what Vercel does at 300 s.

There are 2 warm-up predictions, 6 quiz items (4 single-choice with a named misconception on every wrong option, 1 ordering item, 1 fill-in-the-blank) and 2 think-deeper questions with 4 binary criteria each. The hands-on task is a small `api.py`: the learner turns a list-returning route into a JSON Lines stream, and fixes an SSE route so that its events are named `step` with an `id`, and ends with a `done` event whose data is exactly `[DONE]`. The hidden tests parse both streams.

## Why

The tutor on this site is an SSE route, and the next lessons in the track build on it. A learner who knows the two formats, the failure cases and the deploy limits can read that route and write their own.

## Checked

The task's tests pass on the solution and fail on the starter (`tests/test_lesson_tasks.py`). The content validators pass, and `uv run pytest -q`, `ruff check`, `ruff format --check` and `ty check` pass. The sources were already in `content/sources.yaml` (MIT, FastAPI 0.143.0), so that file is unchanged.

Read first: `content/fastapi/fa12-streaming/lesson.md`.

Closes #84

🤖 Generated with [Claude Code](https://claude.com/claude-code)
