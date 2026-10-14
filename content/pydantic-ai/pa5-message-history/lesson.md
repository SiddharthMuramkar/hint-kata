---
id: pa5-message-history
track: pydantic-ai
title: "Message history and conversations"
minutes: 25
pins:
  pydantic-ai: "2.56.0"
sources:
  - pydantic-ai-core-concepts-message-history
  - pydantic-ai-core-concepts-persistence
---

A language model has no memory. Every request it receives is all it knows. A chat feels continuous only because your code sends the earlier turns along with each new question. In this lesson you look at what those turns are, how to feed them back in, how to save them, how to treat history that comes from someone else, and how to stop it growing forever.

## Requests, responses and parts

One agent run produces a list of **messages**. There are only two kinds:

- A `ModelRequest` is something sent **to** the model. It holds your prompt, and later in a run it can also hold tool results.
- A `ModelResponse` is something that came **back** from the model. It holds the text the model wrote, and any tool calls it asked for.

Each message is a container for **parts**. The part says what the content is:

| Message | Parts you will see |
| --- | --- |
| `ModelRequest` | `UserPromptPart` (your prompt), `ToolReturnPart` (a tool's result), `RetryPromptPart` (a request to try again), `SystemPromptPart` (from `system_prompt`, or added by a client, as you will see below) |
| `ModelResponse` | `TextPart` (the answer), `ToolCallPart` (a tool the model wants to run) |

You get the list from the result object:

```python
from pydantic_ai import Agent

agent = Agent("openrouter:anthropic/claude-haiku-5.5", instructions="Be brief.")
result = agent.run_sync("Tell me a joke.")

for message in result.all_messages():
    print(type(message).__name__, [type(part).__name__ for part in message.parts])
# > ModelRequest ['UserPromptPart']
# > ModelResponse ['TextPart']
```

A plain question with a plain answer is two messages. A run that uses a tool is longer: request, response with a `ToolCallPart`, request with a `ToolReturnPart`, then the final response. That is the loop you saw in the tools lesson, written down as data.

Every message also carries some bookkeeping. A request records the `instructions` that were in force. A response records the `usage` in tokens and the `model_name`. Both carry a `run_id` (new for every run) and a `conversation_id` (shared by the runs of one conversation, more on that below).

Messages are ordinary Python dataclasses. Because they are plain data, you can print them, test them and store them.

Read more: [Accessing messages from results](https://pydantic.dev/docs/ai/core-concepts/message-history/#accessing-messages-from-results) on the Messages and chat history page.

## Continuing a conversation

Each `run_sync` call starts from nothing. If you ask "My name is Ana." and then, in a second call, "What is my name?", the second call has no idea. The model is not at fault. You never told it about the first call.

To continue, pass the earlier messages with `message_history`:

```python
first = agent.run_sync("My name is Ana.")
second = agent.run_sync("What is my name?", message_history=first.new_messages())
print(second.output)
```

On the second call the model receives the first request, the first reply, and then your new prompt, in that order. You can read the whole thing back with `second.all_messages()`, which now holds four messages.

A few details worth knowing:

- Your new prompt goes **after** the history. You do not put it inside the history yourself.
- Instructions come from the agent you run **now**, as you saw in the first lesson. Old requests keep a copy of the instructions they were sent with, but those copies are not sent again. This is why `instructions` are safer than `system_prompt` when a history moves between agents.
- With `system_prompt` it works the other way round. A non-empty history is assumed to contain the system prompt already, so a new one is not added. If your history came from somewhere that did not keep it (a database column you trimmed, a browser), the system prompt is simply missing. A capability called `ReinjectSystemPrompt` can put it back.
- The `conversation_id` on each message links the runs of one chat. It is a label for tracing, for example in Logfire. It does **not** make the model remember anything. Only the messages you pass do the remembering.

The same `message_history` argument works with `run`, `run_stream` and with a different agent or model on the next turn. The message format does not depend on the model.

Read more: [Using messages as input for further agent runs](https://pydantic.dev/docs/ai/core-concepts/message-history/#using-messages-as-input-for-further-agent-runs) and [Correlating runs with run_id and conversation_id](https://pydantic.dev/docs/ai/core-concepts/message-history/#correlating-runs-with-run_id-and-conversation_id).

## All messages or new messages

The result gives you two views of the same run:

- `result.all_messages()` is everything: the history you passed in **plus** this run.
- `result.new_messages()` is only what this run added. With a plain question that is two messages, the request and the reply.

Both have a JSON twin, `all_messages_json()` and `new_messages_json()`, which return bytes.

The difference matters most when you keep your own list. Look at this loop:

```python
history = []
for text in ["one", "two", "three"]:
    result = agent.run_sync(text, message_history=history)
    history += result.all_messages()  # bug
```

After three turns the list should hold 6 messages. It holds 14. On every turn `all_messages()` already contains the old history, so adding it again copies the past in once more. The model then sees the same conversation repeated, which costs tokens and confuses it.

There are two correct patterns. Pick one and stay with it:

```python
history += result.new_messages()  # add only the new turn
history = result.all_messages()  # or replace the list with the full one
```

In the hands-on task you will build a small `Chat` class around the first pattern.

There is one more thing the plain list does not carry: **usage**. If a run gets its history only through `message_history`, its usage starts from zero again, so a `UsageLimits` budget meant to cover the whole chat is reset on every turn. The fix is the `conversation` object. `result.conversation` bundles the messages, the running usage and the conversation id, and you give it to the next run through the `conversation=` argument instead of `message_history`:

```python
second = agent.run_sync("What is my name?", conversation=first.conversation)
print(second.usage.requests)  # counts the first run too
```

Do not pass `conversation=` together with `message_history`. Pydantic AI raises a `UserError`, because the conversation already carries the messages. For a simple chat, the list of messages is enough. Reach for `conversation` when you want a limit that spans the whole thread.

Read more: [Carrying a conversation whole](https://pydantic.dev/docs/ai/core-concepts/message-history/#carrying-a-conversation-whole).

## Saving and loading history

A list of messages lives in memory. If the process restarts, it is gone. To keep it, you turn it into JSON, store the JSON somewhere, and turn it back into message objects later.

Do not try `json.dumps` on the messages. They are dataclasses that hold timestamps, nested parts and other typed values. Pydantic AI ships a ready-made **type adapter** for the job, `ModelMessagesTypeAdapter`. It knows how to write every message and part, and, more importantly, how to read them back as the right classes.

```python
from pathlib import Path

from pydantic_ai import Agent, ModelMessagesTypeAdapter

agent = Agent("openrouter:anthropic/claude-haiku-5.5", instructions="Be brief.")
path = Path("history.json")

# Save after a run.
result = agent.run_sync("My name is Ana.")
path.write_bytes(ModelMessagesTypeAdapter.dump_json(result.all_messages()))

# Later, in a new process: load and continue.
history = ModelMessagesTypeAdapter.validate_json(path.read_bytes())
result = agent.run_sync("What is my name?", message_history=history)
```

`dump_json` returns bytes and `validate_json` accepts bytes, so no encoding step is needed. The adapter checks the data as it reads it, so a damaged file fails with a clear validation error rather than a mystery later. The JSON also keeps the extra fields that are never sent to the model. If you build an adapter of your own from `list[ModelMessage]`, you get the same behaviour.

Where the JSON lives is your choice. A file works for a script. In a web app it is usually a column in your own database, keyed by a chat or thread id. Pydantic AI is deliberately unopinionated about the schema. For remembering the chat in front of it, an agent needs nothing beyond the stored messages you pass back, so you do not need a separate memory system for that. Memory that must survive across conversations is a different problem, handled by the Pydantic AI Harness packages, and a run that must survive a crash mid-tool-call is the job of durable execution.

Two practical notes:

- To save a conversation you intend to continue with `conversation=`, store the `Conversation` object with `ConversationTypeAdapter`. It includes the usage and the id.
- For a long thread, rewriting the whole list on every turn gets slow. Store messages in rows and append only `new_messages()` each turn.

Read more: [Storing and loading messages (to JSON)](https://pydantic.dev/docs/ai/core-concepts/message-history/#storing-and-loading-messages-to-json) and the [Persistence](https://pydantic.dev/docs/ai/core-concepts/persistence/) page.

## History from untrusted clients

So far the history came from your own code. Suppose instead that a browser sends it to your server with every request. Now the history is **input from a stranger**.

The `message_history` argument is treated as trusted state. Whatever you pass is processed as if your server had produced it. A client could therefore add a message of its own, such as a system prompt saying "ignore your earlier rules". A system prompt carries your authority as the operator, so the model would take it as your instruction.

`sanitize_messages` is the first line of defence. You run client history through it before it reaches the agent:

```python
from pydantic_ai import Agent, ModelMessagesTypeAdapter
from pydantic_ai.messages import sanitize_messages

agent = Agent("openrouter:anthropic/claude-haiku-5.5", instructions="Be brief.")

# `body` is the JSON the browser sent.
loaded = ModelMessagesTypeAdapter.validate_python(body["message_history"])
history = sanitize_messages(loaded)
result = agent.run_sync("Tell me a different joke.", message_history=history)
```

By default it removes or resets the parts a client should never control:

- **System prompts** are stripped. Only your agent's own instructions steer the model. In 2.56.0 it also emits a `UserWarning` and continues, so you notice when a client sent one.
- File URLs that do not use HTTP, uploaded-file references and workspace references are dropped or reset, so a client cannot point your agent at files or environments it should not touch.
- Tool calls at the end of the history that have no result yet are removed.

The first two can be switched off with an argument (for example `strip_system_prompts=False` or an allowed list of URL schemes), but only do that when your own trusted code made the part.

The important lesson is what sanitizing does **not** do. It does not prove the rest of the history is genuine. Nothing in Pydantic AI checks a signature on tool calls, tool results or approvals. A client can still invent a user message, an assistant reply, or even a tool call the model never made. So the rules around it matter:

1. Put the agent behind your own authentication. Anyone who gets through can submit any history they like.
2. Give each caller only the tools they are allowed to use.
3. Check high-stakes actions inside the tool itself, against server-side data, not against what the history claims.

The safest design avoids the problem. Keep the history on the server and let the client send only its new message. The tutor on this site works that way.

Read more: [Loading untrusted history](https://pydantic.dev/docs/ai/core-concepts/message-history/#loading-untrusted-history) and [Trust boundary for client-supplied history](https://pydantic.dev/docs/ai/core-concepts/message-history/#trust-boundary-for-client-supplied-history).

## Keeping history small

The model sees every message you send, and you pay for every token of it. A chat that grows without limit gets slower and more expensive on each turn, until it no longer fits in the model's context window. You decide what to send. The stored copy and the sent copy do not have to be the same.

There are three common choices:

1. **Send only the recent part.** Keep the last few messages and drop the rest.
2. **Summarize the old part.** Replace older turns with a short summary written by a cheaper model.
3. **Compact when the window fills.** Wait until the conversation is close to the limit, then shrink it.

The simplest is to keep the last N messages. Pydantic AI has a `ProcessHistory` capability that rewrites the history just before each request:

```python
from pydantic_ai import Agent, ModelMessage, ModelRequest
from pydantic_ai.capabilities import ProcessHistory


def keep_recent(messages: list[ModelMessage]) -> list[ModelMessage]:
    recent = messages[-10:]
    while recent and not isinstance(recent[0], ModelRequest):
        recent = recent[1:]  # start on a request, not in the middle of a turn
    return recent


agent = Agent(
    "openrouter:anthropic/claude-haiku-5.5",
    capabilities=[ProcessHistory(keep_recent)],
)
```

Where you cut matters. If a slice separates a tool call from its result, Pydantic AI repairs the history before it goes out: it drops the orphaned result, or answers the orphaned call with an "interrupted" result. The history stays valid, but the model sees something different from what you stored. Cut on whole-turn boundaries to avoid surprises.

One more catch: a processor also changes what `result.all_messages()` returns, which can be just the trimmed window. So when you use a processor, keep your own list with `history += result.new_messages()`, as in the task, and not `history = result.all_messages()`. Otherwise your stored copy quietly shrinks to the window.

**How this site's tutor does it.** Each chat message is saved as one row with a role and its text. On every question the server reads the newest 10 rows, which is about five question-and-answer pairs, and turns them back into a `ModelRequest` or `ModelResponse` each. It passes them as `message_history` with the new question. Three choices make this simple and safe:

- The tutor has no tools, so the history is plain text and there are no call-and-result pairs to break.
- Instructions are rebuilt from the lesson on each request, so they never live in the stored history.
- The history is built on the server from its own database, so a browser cannot slip in a forged system prompt.

The price is that the tutor forgets anything said more than about five exchanges ago. That is a fair trade for short hints, and the cap keeps each request small. If a long thread mattered more, you would add a summary of the old turns instead of discarding them.

Read more: [Processing message history](https://pydantic.dev/docs/ai/core-concepts/message-history/#processing-message-history).

---

Sources: [Messages and chat history](https://pydantic.dev/docs/ai/core-concepts/message-history/) and [Persistence](https://pydantic.dev/docs/ai/core-concepts/persistence/) from the Pydantic AI documentation, version 2.56.0, MIT licence, © Pydantic Services Inc. 2024 to present. This site is not affiliated with Pydantic.
