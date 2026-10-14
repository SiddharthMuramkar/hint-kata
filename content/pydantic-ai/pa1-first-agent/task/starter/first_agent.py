"""Your first agent. Fill in the two TODOs."""

import os

from pydantic import BaseModel
from pydantic_ai import Agent

DEFAULT_MODEL = "openrouter:anthropic/claude-haiku-5.5"


class CityFacts(BaseModel):
    """Facts about one city."""

    # TODO 1: add three fields: city (str), country (str) and population (int).


def make_agent() -> Agent[None, CityFacts]:
    """Build the agent. It must return a `CityFacts` object when it runs."""
    # The model string comes from TUTOR_MODEL. An empty value counts as missing.
    model = os.getenv("TUTOR_MODEL") or DEFAULT_MODEL
    # TODO 2: return an Agent for `model` with:
    #   - instructions that contain the word "concise"
    #   - output_type=CityFacts
    raise NotImplementedError(f"build an Agent for {model}")


if __name__ == "__main__":
    # Needs OPENROUTER_API_KEY in your environment. One small paid call.
    result = make_agent().run_sync("Tell me about Lisbon.")
    print(result.output)
    print(result.usage)
