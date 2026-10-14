# Task: read a streamed run two ways

You will write two small async functions. Both take an agent and a prompt, and both read the same kind of run in a different way. One collects the text as it streams. The other watches the events and notes which tools were called.

Open `stream.py` in your workspace. It has two TODO comments.

1. **`collect_deltas(agent, prompt)`**: return the streamed text as a list of deltas.
   - Open the run with `agent.run_stream(prompt)` and loop over `result.stream_text(...)`.
   - Each item must hold only the new text of a chunk, not the text so far.
   - You need one item per chunk. By default Pydantic AI groups chunks that arrive close together. Read the section "Text deltas and cumulative text" to find the option that turns that off.
2. **`tool_names(agent, prompt)`**: return the name of every tool the agent called, in the order it called them.
   - Open the run with `agent.run_stream_events(prompt)` and loop over the events.
   - The event for "the agent is about to run a tool" is `FunctionToolCallEvent`. The tool name is on its `part`.

Both functions are `async def`, so do not use `asyncio.run` inside them.

## How the check works

The hidden tests use a `FunctionModel` with a scripted streamed reply, and set `ALLOW_MODEL_REQUESTS = False`, so no API key is needed. One fake model streams a plain text answer in four chunks. The other calls two tools, `price_of` and then `add_tax`, and then streams its text. The tests check that:

- `collect_deltas` returns exactly the four chunks, one item each.
- `collect_deltas` on the tool run returns only the text of the final answer, not the tool calls.
- `tool_names` returns `["price_of", "add_tax"]` in that order.
- `tool_names` returns an empty list when the model calls no tool.

Press **Check my work** when you are ready. If a test fails, read its message and the lesson sections "Text deltas and cumulative text" and "Seeing every event".
