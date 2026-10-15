# Task: a desk agent that asks a stock agent

You will finish a small delegation. A customer talks to the `desk_agent`. When the customer asks about stock, the desk agent uses its tool `check_stock`. That tool must run a second agent, the `stock_agent`, and give the number back to the desk agent.

Open `desk.py` in your workspace. Everything is written except the tool `check_stock`, which has three TODO comments.

1. Make the tool `async def`. A tool that runs another agent cannot use `run_sync`.
2. Inside the tool, `await stock_agent.run(...)` with the prompt `f"How many {item} do we have?"`. Pass two more things:
   - `deps=ctx.deps`, so the stock agent works on the same `DeskDeps` object,
   - `usage=ctx.usage`, so the stock agent's requests count in the desk agent's total.
3. Return the number the stock agent gave back. That is the `output` of its result.

Do not pass `message_history`. The stock agent should only see the question your tool builds, not the customer's conversation.

## How the check works

The hidden tests put a scripted `FunctionModel` on **both** agents with `override`, and set `ALLOW_MODEL_REQUESTS = False`, so no API key is needed. The desk agent's fake model asks for `check_stock`. The stock agent's fake model asks for `count_in_warehouse` and then answers. Both fake models write their name into a log. The tests check that:

- the final text holds the number from the `DeskDeps` you passed in, and the log reads `desk, stock, stock, desk`,
- the prompt that reaches the stock agent's model names the item, and does not hold the customer's question,
- the stock agent's tool wrote into the same `deps.asked` list,
- `result.usage.requests` is `4` and `result.usage.tool_calls` is `2`,
- a `UsageLimits(request_limit=3)` on the desk run stops the run with `UsageLimitExceeded`, because the stock agent's requests count too.

Press **Check my work** when you are ready. If a test fails, read its message and the lesson sections "Why the delegating tool is async", "Sharing usage and a budget" and "Sharing dependencies".
