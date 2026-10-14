"""A broken copy of support_agent. The learner's tests must FAIL against this one."""

from dataclasses import dataclass, field

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext


@dataclass
class SupportDeps:
    orders: dict[str, float]  # order id -> amount paid
    looked_up: set[str] = field(default_factory=set)  # orders the model has looked up
    refunds: list[str] = field(default_factory=list)  # orders that were refunded


class SupportReply(BaseModel):
    order_id: str
    refunded: bool
    message: str


support_agent = Agent(
    "openai:gpt-5.2",
    deps_type=SupportDeps,
    output_type=SupportReply,
    instructions="You are a support agent. Always call lookup_order before refund.",
    defer_model_check=True,
)


# bug: refund is registered before lookup_order, and it no longer checks that the order was
# looked up. A model that follows the tool list refunds first, and nothing stops it.
@support_agent.tool(sequential=True)
def refund(ctx: RunContext[SupportDeps], order_id: str, amount: float) -> str:
    """Refund an order. The order must be looked up first."""
    if amount > ctx.deps.orders[order_id]:
        raise ModelRetry(f"You can refund at most {ctx.deps.orders[order_id]}.")
    ctx.deps.refunds.append(order_id)
    return f"Refunded {amount} for order {order_id}"


@support_agent.tool(sequential=True)
def lookup_order(ctx: RunContext[SupportDeps], order_id: str) -> float:
    """Return the amount paid for an order."""
    if order_id not in ctx.deps.orders:
        raise ModelRetry(f"Unknown order {order_id!r}. Known orders: {', '.join(ctx.deps.orders)}")
    ctx.deps.looked_up.add(order_id)
    return ctx.deps.orders[order_id]
