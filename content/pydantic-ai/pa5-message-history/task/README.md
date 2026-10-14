# Task: a chat that remembers

You will build a small `Chat` class. It runs an agent, remembers every turn, and can save its history to a JSON file and load it again.

Open `chat.py` in your workspace. `make_agent()` is already written. The `Chat` class has three TODO comments.

1. **`ask(text)`**: run `self.agent` on `text`, passing `self.messages` as `message_history`. Then add **only the messages from this run** to `self.messages`, and return the reply text (`result.output`).
2. **`save(path)`**: write `self.messages` to `path` as JSON, using `ModelMessagesTypeAdapter`.
3. **`load(path)`**: read the JSON at `path` and put the resulting messages in `self.messages`, replacing whatever was there.

Careful with the difference between `result.all_messages()` and `result.new_messages()`. If you add the wrong one to the list, earlier turns get copied in again on every call.

## How the check works

The hidden tests use a `FunctionModel` that records the messages it receives, and set `ALLOW_MODEL_REQUESTS = False`, so no API key or network is needed. They check that:

- `ask` returns the reply text.
- After two `ask` calls, the model's second run saw the first turn: the first prompt, the first reply and the new prompt.
- After three `ask` calls `messages` holds exactly six messages, with no repeats.
- `save` writes a JSON list of messages, and `load` reads it back into real message objects, so a new `Chat` can carry on the conversation.
- `load` replaces the history instead of adding to it, and it reads a history file written by the reference solution.

Press **Check my work** when you are ready. If a test fails, read its message and the lesson sections "All messages or new messages" and "Saving and loading history".

Want to see it work for real? Set `OPENROUTER_API_KEY` and run `uv run python chat.py` from your workspace folder. That makes two small paid calls.
