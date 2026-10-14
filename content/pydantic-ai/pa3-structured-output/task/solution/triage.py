"""Triage agent: turn a support message into a Ticket, and reject answers that break the rules."""

import os
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry

DEFAULT_MODEL = "openrouter:anthropic/claude-haiku-5.5"
MAX_SUMMARY = 120


class Ticket(BaseModel):
    """A support ticket."""

    category: Literal["bug", "billing", "other"]
    priority: int
    summary: str


def make_agent() -> Agent[None, Ticket]:
    """Build the agent. It returns a `Ticket` and rejects bad ones with ModelRetry."""
    # The model string comes from TUTOR_MODEL. An empty value counts as missing.
    model = os.getenv("TUTOR_MODEL") or DEFAULT_MODEL
    agent = Agent(
        model,
        instructions="You triage support messages. Priority 1 is the most urgent, 5 the least.",
        output_type=Ticket,
    )

    @agent.output_validator
    def check_ticket(ticket: Ticket) -> Ticket:
        if not 1 <= ticket.priority <= 5:
            raise ModelRetry("The priority must be a whole number from 1 to 5.")
        if len(ticket.summary) > MAX_SUMMARY:
            raise ModelRetry(
                f"The summary must be at most {MAX_SUMMARY} characters long, "
                f"but it has {len(ticket.summary)}. Shorten it."
            )
        return ticket

    return agent


if __name__ == "__main__":
    # Needs OPENROUTER_API_KEY in your environment. One small paid call.
    result = make_agent().run_sync("My invoice PDF will not open and I need it for tax day!")
    print(result.output)
