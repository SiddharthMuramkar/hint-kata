"""Task: give an agent a price lookup tool that reads its catalogue from dependencies."""

from dataclasses import dataclass

from pydantic_ai import Agent, ModelRetry, RunContext  # noqa: F401  (you will use these)


# TODO 1: make Deps a dataclass with one field, `prices: dict[str, float]`.
@dataclass
class Deps:
    pass


def make_agent() -> Agent[Deps, str]:
    # TODO 2: tell the agent which dependency type it takes (`deps_type=`).
    agent = Agent(
        "test",  # tests swap in a scripted model; the caller picks the real one
        instructions="You are a shop assistant. Use price_of to look up prices; never guess.",
    )

    # TODO 3: register a tool called `price_of` with the decorator that gives the
    # function a RunContext: `def price_of(ctx: RunContext[Deps], item: str) -> float`.
    #   - Write a docstring: the model reads it to decide when to call the tool.
    #   - Look the item up in `ctx.deps.prices`.
    #   - If the item is missing, raise ModelRetry("Unknown item, try one of: ...")
    #     and list the known item names after the colon.

    return agent
