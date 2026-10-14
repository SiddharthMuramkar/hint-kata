"""Reference solution: a chat that remembers earlier turns and can save them to disk."""

import os
from pathlib import Path

from pydantic_ai import Agent, ModelMessage, ModelMessagesTypeAdapter

DEFAULT_MODEL = "openrouter:anthropic/claude-haiku-5.5"


def make_agent() -> Agent[None, str]:
    """The agent behind the chat. The model string comes from TUTOR_MODEL."""
    model = os.getenv("TUTOR_MODEL") or DEFAULT_MODEL
    return Agent(model, instructions="You are a friendly chat partner. Be concise.")


class Chat:
    """One conversation. `messages` is everything said so far, in order."""

    def __init__(self, agent: Agent[None, str] | None = None) -> None:
        self.agent = agent or make_agent()
        self.messages: list[ModelMessage] = []

    def ask(self, text: str) -> str:
        """Send `text` with the stored history, remember the new turn, return the reply."""
        result = self.agent.run_sync(text, message_history=self.messages)
        # new_messages() is only this run's request and reply. Adding all_messages() here
        # would copy the whole earlier history in again on every turn.
        self.messages.extend(result.new_messages())
        return result.output

    def save(self, path: Path) -> None:
        """Write the history to `path` as JSON."""
        path.write_bytes(ModelMessagesTypeAdapter.dump_json(self.messages))

    def load(self, path: Path) -> None:
        """Replace the history with the JSON stored at `path`."""
        self.messages = ModelMessagesTypeAdapter.validate_json(path.read_bytes())


if __name__ == "__main__":
    # Needs OPENROUTER_API_KEY in your environment. Two small paid calls.
    chat = Chat()
    print(chat.ask("My name is Ana. Reply with one short sentence."))
    print(chat.ask("What is my name?"))
    chat.save(Path("chat.json"))
    print(f"Saved {len(chat.messages)} messages to chat.json")
