---
id: pa4-streaming
track: pydantic-ai
title: "Streaming"
minutes: 30
pins:
  pydantic-ai: "2.56.0"
sources:
  - pydantic-ai-core-concepts-agent
  - pydantic-ai-core-concepts-output
  - pydantic-ai-core-concepts-message-history
  - pydantic-ai-guides-testing
---

A model can take many seconds to write a long answer. If you wait for the whole reply, the reader stares at a blank screen. Streaming shows the reply while it is still being written. In this lesson you stream text, stream a structured answer, watch every event of a run (tool calls too), find out when the token count is complete, and see how this site's tutor sends its replies. We ran the examples in this lesson on Pydantic AI 2.56.0. Where a point comes only from the docs, the text says so.

## Starting a streamed run

Besides `run()` and `run_sync()`, the [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/#running-agents) page lists the ways to run an agent. Two of them stream:

- `agent.run_stream()` streams the final output as it arrives. It gives you a `StreamedRunResult`.
- `agent.run_stream_events()` streams every event of the run: the model's output, the tool calls, the tool results, and the finished run.

Both are **async context managers**. You must open them with `async with`:

```python
async with agent.run_stream("Where does 'hello world' come from?") as result:
    async for text in result.stream_text():
        print(text)
```

The `async with` block opens the stream and closes it when the block ends. Leave it out and Python raises a `TypeError`. For example, `async for event in agent.run_stream_events(...)` fails because the object has no `__aiter__`. You need the `as events:` handle that `async with` gives you.

One rule decides what `run_stream` does with tools. It treats the **first output that matches your output type as the final answer**. A tool call that comes before the answer runs as usual, and then the text streams. But if one reply holds both text and a tool call, and the output type is `str`, the [docs say](https://pydantic.dev/docs/ai/core-concepts/agent/#streaming-events-and-final-output) the tool call will not run. If you need every tool to run, use `run_stream_events()` or `agent.iter()`.

## Text deltas and cumulative text

`stream_text()` gives you strings. What each string holds depends on one argument, `delta`. Say the model sends the chunks `Tea `, `costs `, and `2.5.`:

| Call | Item 1 | Item 2 | Item 3 |
|---|---|---|---|
| `stream_text(debounce_by=None)` | `Tea ` | `Tea costs ` | `Tea costs 2.5.` |
| `stream_text(delta=True, debounce_by=None)` | `Tea ` | `costs ` | `2.5.` |

- **Cumulative** (the default, `delta=False`): each item is the whole text so far. You can replace what is on screen each time.
- **Delta** (`delta=True`): each item is only the new piece. You append it, or send it on.

The `debounce_by` argument is the reason the table says `debounce_by=None`. The default is `0.1`, and it groups chunks that arrive within 0.1 seconds into one item. That saves work when the model is fast. We checked what it does to a scripted model that sends all its chunks at once: with the default, both modes gave a single item, `Tea costs 2.5.`. Pass `debounce_by=None` to get one item per chunk. The [Output](https://pydantic.dev/docs/ai/core-concepts/output/#streaming-text) page describes both options.

`stream_text()` only works when the answer is text. If your agent has a structured `output_type`, it raises a `UserError` (`stream_text() can only be used with text responses`). The next section shows what to use.

## Streaming structured output

For a structured answer, use `stream_output()`. The model writes JSON a few characters at a time, so Pydantic AI checks each partial piece with **partial validation**. The [Output](https://pydantic.dev/docs/ai/core-concepts/output/#streaming-structured-output) page explains it.

```python
class Profile(BaseModel):
    name: str
    age: int | None = None
    bio: str = ""


agent = Agent("openai:gpt-5.2", output_type=Profile)

async with agent.run_stream("My name is Ben, I am 35, I like dogs.") as result:
    async for profile in result.stream_output():
        print(profile)
```

Here is what we saw on a scripted model, with `debounce_by=None`:

```text
name='Be' age=None bio=''
name='Ben' age=3 bio=''
name='Ben' age=35 bio='Likes '
name='Ben' age=35 bio='Likes dogs'
name='Ben' age=35 bio='Likes dogs'
```

Read three things from it.

- Each item is a **snapshot of the whole object**, not a delta. Replace what you show. Do not append.
- A string can be cut off in the middle (`'Be'`, then `'Ben'`). Show it as unfinished.
- The last snapshot can arrive twice. Treat each item as "the new state", not as one event to count.

Fields need defaults for this to work well. We tried the same stream with three required fields and no snapshot came out until all three had a value. Snapshots that fail validation are skipped, not raised. With defaults, the first snapshot came as soon as `name` began. When the stream ends, `await result.get_output()` returns the final, fully validated object.

If you use an output validator or an output function, know that it runs for **every partial snapshot** and once more for the final one. Check `ctx.partial_output`. It is `True` for the partial calls and `False` for the last one. Skip side effects, such as saving to a database, when it is `True` (see [partial output in validators](https://pydantic.dev/docs/ai/core-concepts/output/#handling-partial-output-in-output-validators)).

The docs add that this works when the model can stream tool arguments. For a model that cannot, try Native Output or Prompted Output.

## Seeing every event

`run_stream()` hands you the final answer. Sometimes you want more: show "calling get_forecast..." in the UI, log every tool, or keep the raw events. For that, use `run_stream_events()`:

```python
async with agent.run_stream_events("How much is tea?") as events:
    async for event in events:
        print(type(event).__name__)
```

The stream has two kinds of events, plus a last one. The first kind describes **what the model is writing**:

- `PartStartEvent`: a new part of the reply begins. A part can be text, a tool call or thinking. The event holds the first piece.
- `PartDeltaEvent`: the next piece of that part. Its `delta` is a `TextPartDelta`, a `ToolCallPartDelta` or a `ThinkingPartDelta`.
- `PartEndEvent`: the part is complete.
- `FinalResultEvent`: the reply has become the final result. For text, its `tool_name` is `None`.

The second kind describes **what the agent runs**:

- `FunctionToolCallEvent`: the model's call is complete and the agent is about to run your function. `event.part.tool_name` is the tool name.
- `FunctionToolResultEvent`: your function returned. `event.part.content` is the value.

The last event is `AgentRunResultEvent`. Its `result` is the finished run, with the `output` and the `usage`.

For a run where the model calls one tool and then answers in text, we saw this order:

```text
PartStartEvent            the tool call begins
PartDeltaEvent            the rest of its arguments
PartEndEvent              the tool call is complete
FunctionToolCallEvent     the agent runs the tool
FunctionToolResultEvent   the tool returned
PartStartEvent            the text begins (request 2)
FinalResultEvent          this reply is the answer
PartDeltaEvent            more text (one event per piece)
PartEndEvent              the text is complete
AgentRunResultEvent       the run is finished
```

Three details to keep in mind.

- The events are raw. For streamed text you must join the `PartStartEvent` content and the following `PartDeltaEvent` pieces yourself. The [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/#streaming-all-events) page says the same.
- Unlike `run_stream()`, `run_stream_events()` always runs the agent to the end, so every tool runs. The docs describe it as a wrapper around `run()` with an event handler.
- A structured answer that comes through an output tool does not use the function-tool events. We saw `OutputToolCallEvent` and `OutputToolResultEvent` for it. So if you list tool names with `FunctionToolCallEvent`, you list only your own tools.

The docs say that if you stop reading and leave the `async with` block, the run is cancelled and the connection is closed. For a stop button, see [Cancelling streams](https://pydantic.dev/docs/ai/core-concepts/output/#cancelling-streams).

## When usage is complete

Usage is the token and request count of the run. In 2.56.0 it is a property, so write `result.usage` with no parentheses. Calling it raises a `TypeError`.

Pydantic AI tells you in its own docstring that `usage` "won't return the full usage until the stream is finished". We saw what that means.

- On a `run_stream()` result, the value was partial before we read the stream (`output_tokens=1`) and complete after the stream ended (`output_tokens=7`). `result.is_complete` flipped from `False` to `True` at the same moment.
- On `run_stream_events()`, the value of `events.usage` stayed partial during the run. Right after the last text piece it still counted only one request. The `AgentRunResultEvent` showed the full total, two requests and one tool call. `event.result.usage` is the safe place to read it.
- If you stop early with `break`, the count stays partial. The docs also warn that usage after a [cancelled stream](https://pydantic.dev/docs/ai/core-concepts/agent/#cancelling-a-run) is partial and depends on the provider. Do not use it for cost-critical accounting.

Messages follow the same rule. Before you read the stream, `result.all_messages()` holds only the request. The [Messages](https://pydantic.dev/docs/ai/core-concepts/message-history/#accessing-messages-from-results) page says the final response is included once the stream has finished.

So the rule is short. Read `usage` and the messages **after** the stream is done.

## How the tutor streams

The tutor on this site uses what you just learned. Here is how a reply travels. The code is in `app/routes/tutor.py`, `app/agents/tutor.py` and `app/static/js/tutor.js`.

1. **The browser** sends `POST /api/tutor/{lesson}` with `fetch`. It reads the response body with a stream reader, splits it on blank lines into server-sent events, and handles five event names: `token`, `ceiling`, `html`, `citations` and `error`. It does not use `EventSource`.
2. **The route** is an async generator. It is declared with `response_class=EventSourceResponse` (from `fastapi.sse`) and it `yield`s a `ServerSentEvent` for each message.
3. **The agent** comes from `make_tutor()`. It has instructions built from the lesson, and no tools. So `run_stream()` is enough. The route calls `async with get_tutor().run_stream(...) as result` and loops over `result.stream_text(delta=True)`. It keeps every delta in a list. It does not pass `debounce_by`, so fast chunks may be grouped (up to 0.1 s).
4. **Tokens are sent only at hint level L4 and above.** Below L4 the server removes code blocks from the whole reply, and it can only do that once the reply is complete. So at lower levels the learner sees no live text. They see the final `html` event.
5. **When the stream ends**, the route joins the deltas, applies the hint ceiling, drops citation markers that are not sections of the lesson, and sends `ceiling`, `html` and `citations`. The browser replaces the live text with the `html` that the server rendered. Last, the route saves the learner's message and the reply to the `chats` table, so a refresh keeps the history.
6. **If the run raises**, the route logs it, sends an `error` event and stops. Nothing is saved for that turn.

Notice how small the streaming part is: one `async with`, one `async for`, and `delta=True`. The rest is rules about what the learner may see.

## Testing a stream without a key

You can test streaming with no API key. `FunctionModel` takes a `stream_function`. It is an async generator that gets the message history and an `AgentInfo`. It yields the reply a piece at a time. This is the same idea as in the [Unit Testing](https://pydantic.dev/docs/ai/guides/testing/#unit-testing-with-functionmodel) page, but streamed.

```python
async def scripted(messages, info):
    if not any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
        yield {0: DeltaToolCall(name="price_of", json_args='{"item": "te', tool_call_id="c1")}
        yield {0: DeltaToolCall(json_args='a"}')}
    else:
        for chunk in ["Tea ", "costs ", "2.5."]:
            yield chunk


agent = Agent(FunctionModel(stream_function=scripted))
```

In these scripts, one reply is either all text pieces (strings) or all tool-call pieces (dicts of `DeltaToolCall`). The first piece of a call holds the name. Later pieces hold more `json_args`. Check the `ToolReturnPart` in the history to know which request you are on.

Tips for tests:

- Pass `debounce_by=None` to `stream_text()` so each scripted chunk is its own item. A scripted model is so fast that the default groups them all.
- Set `models.ALLOW_MODEL_REQUESTS = False`, as in the lesson on tools and dependencies, so a mistake cannot reach a real model.
- Test code that is `async` with `asyncio.run(...)` inside a normal test function. You need no extra plugin.

## Watch it run

The trace below shows a streamed run of an agent with one tool, `get_forecast`. It was recorded with a scripted `FunctionModel` and `run_stream_events()`, so no API key was involved. The model streams a tool call in two pieces. The agent runs the tool. The model then streams its answer in pieces, and the last event ends the run. Step through it and answer the two prediction questions. Try to tell the Part events (the model writing) from the FunctionTool events (the agent running your code).

Sources: [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/), [Output](https://pydantic.dev/docs/ai/core-concepts/output/), [Messages and chat history](https://pydantic.dev/docs/ai/core-concepts/message-history/) and [Unit Testing](https://pydantic.dev/docs/ai/guides/testing/) from the Pydantic AI documentation, version 2.56.0, MIT licence, © Pydantic Services Inc. This site is not affiliated with Pydantic.
