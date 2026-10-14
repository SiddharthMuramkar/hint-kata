"""Task: give an agent a price lookup tool that reads its catalogue from dependencies."""

from dataclasses import dataclass

from pydantic_ai import Agent, ModelRetry, RunContext


@dataclass
class Deps:
    """Everything the tool needs, passed in at run time instead of read from a global."""

    prices: dict[str, float]


def make_agent() -> Agent[Deps, str]:
    agent = Agent(
        "test",  # tests swap in a scripted model; the caller picks the real one
        deps_type=Deps,
        instructions="You are a shop assistant. Use price_of to look up prices; never guess.",
    )

    @agent.tool
    def price_of(ctx: RunContext[Deps], item: str) -> float:
        """Return the price of an item from the shop catalogue.

        Args:
            item: The item name exactly as it appears in the catalogue, e.g. "tea".
        """
        if item not in ctx.deps.prices:
            known = ", ".join(sorted(ctx.deps.prices))
            raise ModelRetry(f"Unknown item, try one of: {known}")
        return ctx.deps.prices[item]

    return agent
