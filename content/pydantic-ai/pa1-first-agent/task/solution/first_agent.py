"""Reference solution: a first agent with instructions and a structured output."""

import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent

DEFAULT_MODEL = "openrouter:anthropic/claude-haiku-5.5"


class CityFacts(BaseModel):
    """Facts about one city."""

    city: str
    country: str
    population: int = Field(description="Approximate number of people")


def make_agent() -> Agent:
    """Build the agent. It must return a `CityFacts` object when it runs."""
    # The model string comes from TUTOR_MODEL. An empty value counts as missing.
    model = os.getenv("TUTOR_MODEL") or DEFAULT_MODEL
    return Agent(
        model,
        instructions=(
            "You give facts about a city. Be concise. "
            "If you are not sure of the population, give your best estimate."
        ),
        output_type=CityFacts,
    )


if __name__ == "__main__":
    # Needs OPENROUTER_API_KEY in your environment. One small paid call.
    result = make_agent().run_sync("Tell me about Lisbon.")
    print(result.output)
    print(result.usage)
