"""Task: let a desk agent ask a stock agent how many units are left."""

from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext


@dataclass
class DeskDeps:
    stock: dict[str, int]  # item -> units in the warehouse
    asked: list[str] = field(default_factory=list)  # filled in by the stock agent's tool


stock_agent = Agent(
    "openai:gpt-5.2",  # real model name; the tests never reach it
    name="stock_agent",
    deps_type=DeskDeps,
    output_type=int,
    instructions="Use count_in_warehouse to look up the item, then return the number.",
    defer_model_check=True,  # do not look for an API key when this module is imported
)

desk_agent = Agent(
    "openai:gpt-5.2",
    name="desk_agent",
    deps_type=DeskDeps,
    instructions="Answer stock questions for customers. Use check_stock to ask the stock team.",
    defer_model_check=True,
)


@stock_agent.tool
def count_in_warehouse(ctx: RunContext[DeskDeps], item: str) -> int:
    """Return how many units of an item are in the warehouse."""
    ctx.deps.asked.append(item)
    return ctx.deps.stock.get(item, 0)


# TODO 1: a tool that runs another agent must be `async def`. Change `def` to `async def`.
@desk_agent.tool
def check_stock(ctx: RunContext[DeskDeps], item: str) -> int:
    """Ask the stock team how many units of an item we have."""
    # TODO 2: run `stock_agent` with `await`. The prompt is f"How many {item} do we have?".
    #   - share the dependencies: `deps=ctx.deps`
    #   - share the usage counter: `usage=ctx.usage`
    # TODO 3: return the number the stock agent gave back (its `output`).
    raise NotImplementedError("finish the delegation")
