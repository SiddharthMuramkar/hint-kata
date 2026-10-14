"""Triage agent: turn a support message into a Ticket, and reject answers that break the rules."""

import os
from typing import Literal  # noqa: F401  (you will use it in TODO 1)

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry  # noqa: F401  (you will use ModelRetry)

DEFAULT_MODEL = "openrouter:anthropic/claude-haiku-5.5"
MAX_SUMMARY = 120


class Ticket(BaseModel):
    """A support ticket."""

    # TODO 1: add three plain fields (no Field(...) constraints, the validator checks the rules):
    #   category: Literal["bug", "billing", "other"]
    #   priority: int
    #   summary: str


def make_agent() -> Agent[None, Ticket]:
    """Build the agent. It returns a `Ticket` and rejects bad ones with ModelRetry."""
    # The model string comes from TUTOR_MODEL. An empty value counts as missing.
    model = os.getenv("TUTOR_MODEL") or DEFAULT_MODEL
    agent = Agent(
        model,
        instructions="You triage support messages. Priority 1 is the most urgent, 5 the least.",
        output_type=Ticket,
    )

    # TODO 2: register an output validator on `agent` (the decorator is `@agent.output_validator`).
    # It receives the Ticket and must return it. Before returning:
    #   - if the priority is not from 1 to 5, raise ModelRetry with a message that says the
    #     priority must be a whole number from 1 to 5.
    #   - if the summary is longer than MAX_SUMMARY (120) characters, raise ModelRetry with a
    #     message that says the summary must be at most 120 characters long.

    return agent


if __name__ == "__main__":
    # Needs OPENROUTER_API_KEY in your environment. One small paid call.
    result = make_agent().run_sync("My invoice PDF will not open and I need it for tax day!")
    print(result.output)
