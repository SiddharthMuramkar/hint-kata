---
id: pa12-multi-agent-and-mcp
track: pydantic-ai
title: "Multi-agent apps and the MCP client"
minutes: 40
pins:
  pydantic-ai: "2.56.0"
  fastmcp: "4.1.0"
sources:
  - pydantic-ai-guides-multi-agent-applications
  - pydantic-ai-mcp-client
  - pydantic-ai-capabilities-overview
  - mcp-docs-intro
---

One agent with a few tools covers most apps. Sometimes a job is better split: one agent talks to the user, and another does a narrow piece of work with its own instructions, tools or model. In this lesson you build that split by hand, share the dependencies and the usage budget between the agents, and test it with a fake model on each side. Then you connect an agent to tools that live in a separate program, using the MCP client. Last, you see where capabilities fit, because they are the bundle that holds all of this. We ran every Python example on Pydantic AI 2.56.0. The MCP examples also used `fastmcp` 4.1.0. Where a point comes only from the docs, the text says so.

## Start with one agent

The [Multi-agent Applications](https://pydantic.dev/docs/ai/guides/multi-agent-applications/) guide lists five levels, from simple to hard:

1. One agent. Most of the docs are about this.
2. Delegation: an agent uses another agent through a tool.
3. Programmatic hand-off: one agent runs, then your own code calls another.
4. Graph-based control flow: a state machine decides which agent runs next. This is for the most complex cases.
5. Deep agents: autonomous agents that plan, work with files, delegate and run code in a sandbox.

You can mix levels in one app. The sensible habit is to stay on the lowest level that works. Each extra agent is at least one extra model request, so it costs time and money, and it gives you one more thing to test. That last sentence is our advice, not the docs. This lesson covers levels 2 and 3. The graph and the deep-agent level are left to the docs.

## Delegation is an agent inside a tool

In delegation, the first agent (the parent) calls a tool. The tool runs a second agent (the delegate), waits for it, and returns what it said. Then the parent carries on. The parent keeps control the whole time. The guide says that if you want to hand control over completely, you should use an output function instead.

Here is a small kitchen app. The cook agent answers questions. For stock levels it asks the pantry agent, which reads the shelves.

```python
# kitchen.py
from dataclasses import dataclass, field

from pydantic_ai import Agent, RunContext


@dataclass
class KitchenDeps:
    shelves: dict[str, int]  # ingredient -> how many we have
    asked: list[str] = field(default_factory=list)  # filled in by the delegate's tool


pantry_agent = Agent(
    "openai:gpt-5.2",
    name="pantry_agent",
    deps_type=KitchenDeps,
    output_type=int,
    instructions="Use shelf_count to look up the ingredient, then return the number.",
    defer_model_check=True,
)

cook_agent = Agent(
    "openai:gpt-5.2",
    name="cook_agent",
    deps_type=KitchenDeps,
    instructions="Answer questions about what we can cook. Use check_pantry for stock.",
    defer_model_check=True,
)


@pantry_agent.tool
def shelf_count(ctx: RunContext[KitchenDeps], ingredient: str) -> int:
    """Return how many units of an ingredient are on the shelves."""
    ctx.deps.asked.append(ingredient)
    return ctx.deps.shelves.get(ingredient, 0)


@cook_agent.tool
async def check_pantry(ctx: RunContext[KitchenDeps], ingredient: str) -> int:
    """Ask the pantry team how many units of an ingredient we have."""
    result = await pantry_agent.run(
        f"How many {ingredient} do we have?",
        deps=ctx.deps,  # same dependencies object
        usage=ctx.usage,  # same usage counter
    )
    return result.output
```

Read `check_pantry` closely. It is an ordinary tool, as in the lesson on tools and dependencies. Its body happens to call `pantry_agent.run(...)` and return the delegate's `output`. The delegate returns an `int` and the tool returns an `int`, so there is nothing to convert.

Two small points from the guide. Agents are stateless and meant to be global, so you do not put an agent into the dependencies. And `name=` is optional, but with more than one agent it labels each run in traces, so you can tell parent from delegate. The `defer_model_check=True` is the same as in the testing lesson: it lets the file be imported with no API key.

The guide mentions one more route. The Pydantic AI Harness, a separate package of ready-made capabilities, has a `SubAgents` capability. You hand it a list of named agents and it adds one `delegate_task(agent_name, task)` tool for you. The guide says to write the tool by hand, as above, when you need your own tool schema, checks on the arguments, or the parent's message history passed down. We did not run `SubAgents`.

## Why the delegating tool is async

The tool above is `async def` and uses `await ...run(...)`. That is required. We tried the same tool as a plain `def` that calls `pantry_agent.run_sync(...)`. The run stopped with a `UserError`. The message says `run_sync()` and `run_stream_sync()` cannot be used inside a synchronous tool, because they can deadlock the run, and it tells you to make the function `async def` and `await agent.run(...)`.

Only the delegating function has to be async. We started the parent with `run_sync` in our runs and it was fine, as the guide also shows. If the tool must also do blocking work, the guide says to keep it `async def` and push that part into `asyncio.to_thread()`.

## Sharing usage and a budget

Every run counts its own requests and tool calls. If the delegate's run starts with a fresh counter, the parent never sees that work. Passing `usage=ctx.usage` makes the delegate add to the parent's counter, so `result.usage` at the end covers both agents.

We ran the kitchen app with a fake model on each side (the testing section below shows how). With `usage=ctx.usage`:

- `result.usage.requests` was `4`: two from the cook, two from the pantry.
- `result.usage.tool_calls` was `2`: `check_pantry` and `shelf_count`. The final answer of each agent is not counted as a tool call.

We then removed the `usage=` line. The same run gave `requests=2` and `tool_calls=1`. The delegate's work had vanished from the total.

That matters for limits. `UsageLimits` is how you stop a run that costs too much or loops. The guide lists `request_limit`, `total_tokens_limit`, `tool_calls_limit` and `cost_limit`. A limit set on the parent run looks at the parent's counter. We ran the kitchen app with `UsageLimits(request_limit=3)`.

- With `usage=ctx.usage`, the run raised `UsageLimitExceeded`. The cook used one request and the pantry used two, so the cook's second request would have been the fourth.
- Without it, the same limit never fired, because the counter only held the cook's two requests.

The guide adds two notes. The agents in a delegation may use different models. The total then still adds up per-response cost where it can be worked out, but it cannot be rebuilt from the token totals alone, because models are priced differently. So set limits. And if the tool runs inside a Temporal activity (a way to run agents that survive restarts), the tool gets a copy of the run context, so `usage=ctx.usage` does not carry the delegate's usage back. We did not test that case.

## Sharing dependencies

The delegate has its own `deps_type`. The guide says the delegate usually needs the same dependencies as the parent, or a subset of them. In the code above, `deps=ctx.deps` hands the parent's object straight to the delegate. In our run, the delegate's tool appended to `ctx.deps.asked`, and after the run `deps.asked` held `["eggs"]`. So both agents worked on the same object, not on a copy.

You could build new dependencies inside the tool instead. The guide says you may, but warns that it is often slower than reusing connections that the parent already opened. Its larger example passes a shared `httpx` client and an API key this way.

## What a delegate sees and what happens when it fails

A delegate starts a run of its own. In our run its model saw one user prompt: the text the tool built (`How many eggs do we have?`). It did not see the user's original question. The guide says the same about `SubAgents`: each delegation has its own run and its own message history, so the delegate never sees the parent conversation. If the delegate needs the earlier chat, pass `message_history=` to its run, as in the next section.

Failure is plain Python. We scripted a delegate whose model raised `RuntimeError("boom")`. The error came out of `await delegate.run(...)`, out of the tool, and ended the parent run with the same `RuntimeError`. If the parent should survive, catch the error in the tool and return text, or raise `ModelRetry` to let the parent try again. The docs do not walk through this. It is how any exception in a tool behaves.

## Hand-off where your code picks the next agent

In a hand-off no agent calls another. Your code runs one agent, looks at the result, and decides which agent runs next. The agents need not share dependencies. Pass `message_history=` if the next agent should see what was said before. The Message history lesson explains that argument. Pass the same `RunUsage` object to every run if you want one total.

```python
# booking.py
import asyncio

from pydantic import BaseModel
from pydantic_ai import Agent, RunUsage


class Seat(BaseModel):
    row: int
    letter: str


flight_agent = Agent(
    "openai:gpt-5.2",
    instructions="Suggest one flight number for the trip.",
    defer_model_check=True,
)
seat_agent = Agent(
    "openai:gpt-5.2",
    output_type=Seat,
    instructions="Pick a seat that fits the traveller's wish.",
    defer_model_check=True,
)


async def book(trip: str, wish: str) -> tuple[str, Seat, RunUsage]:
    usage = RunUsage()
    flight = await flight_agent.run(trip, usage=usage)
    seat = await seat_agent.run(wish, message_history=flight.all_messages(), usage=usage)
    return flight.output, seat.output, usage


if __name__ == "__main__":
    print(asyncio.run(book("Paris to Rome", "a window seat")))
```

In our run, with a fake model for each agent, `usage.requests` was `2` and the seat agent's model received three messages: the first prompt, the flight agent's answer, and the new wish. Between the two calls you can do anything: ask the user, check a database, or stop if the first agent failed. The guide's longer example uses a union output type (`FlightDetails | Failed`) so that an agent can say "I could not find one" and your code can branch on it.

When should you pick hand-off over delegation? Use delegation when the model should decide whether and when to call the helper. Use hand-off when your code knows the order, or a person must be in the loop. That is our rule of thumb. The guide describes the two patterns and does not rank them.

## Testing with FunctionModel on both agents

You test a multi-agent app the way you tested one agent. Block real requests, and put a fake model in each agent with `override`. Use `FunctionModel` when you must choose each reply. A `with` statement can hold two overrides.

```python
# test_kitchen.py
from kitchen import KitchenDeps, cook_agent, pantry_agent
from pydantic_ai import models
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False


def call(name: str, **args: object) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart(name, args)])


def scripted(who: str, log: list[str], *replies: ModelResponse) -> FunctionModel:
    """A fake model that returns the replies one by one and notes who was asked."""
    remaining = iter(replies)

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        log.append(who)
        return next(remaining)

    return FunctionModel(respond)


def test_the_cook_asks_the_pantry() -> None:
    log: list[str] = []
    deps = KitchenDeps(shelves={"eggs": 6})
    answer = ModelResponse(parts=[TextPart("6 eggs")])
    cook = scripted("cook", log, call("check_pantry", ingredient="eggs"), answer)
    pantry = scripted(
        "pantry", log, call("shelf_count", ingredient="eggs"), call("final_result", response=6)
    )
    with cook_agent.override(model=cook), pantry_agent.override(model=pantry):
        result = cook_agent.run_sync("Can we make an omelette?", deps=deps)
    assert result.output == "6 eggs"
    assert log == ["cook", "pantry", "pantry", "cook"]
    assert deps.asked == ["eggs"]
    assert result.usage.requests == 4
    assert result.usage.tool_calls == 2
```

The `log` list shows the order of the whole conversation: the cook asks, the pantry takes two turns, then the cook answers. The delegate's final answer is a call to `final_result` with the key `response`, because its output type is a plain `int`, which is wrapped for the model. The assertions check four things: the answer, the interleaving, the shared dependencies and the shared usage. If someone deletes `usage=ctx.usage`, the last two lines fail.

One catch from the testing lesson still applies. `capture_run_messages()` around this run gave us four messages, all of them the cook's. The pantry's messages were not there. To check what the delegate was sent, record it inside the delegate's fake model, as we did with `log`, or look at the `messages` argument there. To test a budget, run the same script with `usage_limits=UsageLimits(request_limit=3)` and expect `UsageLimitExceeded`. We did that, and `log` then held `["cook", "pantry", "pantry"]`: the cook never got its second turn.

## What MCP is

So far every tool was Python code in your own app. The Model Context Protocol (MCP) is an open standard for connecting AI applications to outside systems, such as files, databases, search tools and prepared prompts. The [MCP introduction](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro) compares it to a USB-C port: one standard plug, so a tool built once works in many applications. An MCP server offers tools. An MCP client, which is the part inside an AI application, connects to the server and passes those tools to the model.

Pydantic AI can be an MCP client. The [MCP Client](https://pydantic.dev/docs/ai/mcp/client/) page says the class that does it is `MCPToolset`. It is a toolset, so you put it in the `toolsets` argument of an `Agent`, like a bundle of tools. The page says to install either `pydantic-ai`, or `pydantic-ai-slim` with the `mcp` extra. This site uses the slim package without that extra, so we ran the MCP examples in a throwaway environment with `pydantic-ai-slim[mcp]` and `fastmcp` (which we needed to write a server for the examples). The hands-on task does not need MCP.

## Connecting an MCPToolset

The first argument of `MCPToolset` tells it where the server is. The page lists five options:

- a URL, which means Streamable HTTP, or the older SSE if the path ends in `/sse`,
- a path to a local Python or Node.js script, which it starts as a program and talks to over stdin and stdout,
- a FastMCP transport object, for full control,
- a ready-made `fastmcp.Client`,
- a FastMCP server that lives in the same Python process, which needs no network.

The page says Streamable HTTP is the recommended way to reach a remote server, and the SSE transport is deprecated. The server must already be running. Pydantic AI does not start an HTTP server for you.

The in-process option is the best one for tests and for learning, so we used it. This script is complete and needs no API key or network.

```python
# calc_client.py
import asyncio

from fastmcp import FastMCP
from pydantic_ai import Agent, models
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False

server = FastMCP("calc")


@server.tool()
async def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


agent = Agent("openai:gpt-5.2", toolsets=[MCPToolset(server)], defer_model_check=True)


def script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
    if not returns:
        return ModelResponse(parts=[ToolCallPart("add", {"a": 7, "b": 5})])
    return ModelResponse(parts=[TextPart(f"The answer is {returns[-1].content}")])


async def main() -> None:
    with agent.override(model=FunctionModel(script)):
        result = await agent.run("What is 7 plus 5?")
    print(result.output)  # The answer is 12


asyncio.run(main())
```

What happened, step by step. The agent asked the server which tools it has and showed them to the model under their own names, so the model saw a tool called `add`. Our fake model asked for `add(7, 5)`. The toolset sent that call to the server. The server returned `12`, and the next model turn used it. In the run, `result.usage` showed `requests=2` and `tool_calls=1`. The MCP tool counted like any other tool.

The agent opens its connections when it needs them. The docs say you can wrap code in `async with agent:` to open and close all MCP connections yourself, which also starts and stops stdio subprocesses. You can do the same with `async with toolset:` if you share one toolset between agents. If you do neither, the toolset opens and closes as needed.

A real setup may use a local program as the server. The stdio transport starts it for you, for example `MCPToolset(StdioTransport(command='python', args=['mcp_server.py']))` from `fastmcp.client.transports`. The page also covers loading many servers from a JSON file with `load_mcp_toolsets()`. It warns that such a file chooses which programs to start and can read environment variables, so you must only load files you control. We did not run the stdio or file examples.

## Tool errors and name clashes

When an MCP tool fails on the server, what should the model see? The `tool_error_behavior` setting of `MCPToolset` chooses between three behaviours:

- `'retry'` is the default. The error becomes a `ModelRetry`, so the model gets a retry prompt and may fix its call.
- `'failed'` records the call as a failed tool result, and the model decides what to do next.
- `'error'` lets the exception escape and ends the run, so your code handles it.

We checked the default. We added a `divide` tool to the server that raises `ValueError("b must not be zero")`. The fake model called it with `b=0`. The next request held a `RetryPromptPart` for `divide`, whose content was `Error calling tool 'divide': b must not be zero`. The model then called it with valid numbers and the run finished. This is the retry flow you tested in the testing lesson, now fed by a remote server.

Two servers may offer a tool with the same name. `.prefixed('calc')` on a toolset adds a prefix to all its tool names. We saw the tools of our server arrive as `calc_add` and `calc_divide`. In a delegation app, prefixes also stop an MCP tool from clashing with a tool you wrote.

## One toolset is one identity

An `MCPToolset` keeps one connection to its server, and every run that uses it shares that connection. The docs stress what follows from that. If your users each have their own credentials for the server, one shared toolset is the wrong tool. Reading the credentials from a task-local variable inside an `auth` object does not work on a shared instance. Overlapping runs would quietly send requests with the credentials of whichever run opened the connection first.

The fix in the docs is to give each run its own toolset, built inside the run from its dependencies. The example below comes from the docs and we did not run it, because it needs a server over HTTP.

```python
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext
from pydantic_ai.mcp import MCPToolset


@dataclass
class UserDeps:
    mcp_token: str


agent = Agent("openai:gpt-5.2", deps_type=UserDeps, defer_model_check=True)


@agent.toolset(per_run_step=False)
def user_mcp_server(ctx: RunContext[UserDeps]) -> MCPToolset:
    return MCPToolset("http://localhost:8000/mcp", auth=ctx.deps.mcp_token)
```

The function runs once per run (`per_run_step=False`), reads the token from `ctx.deps`, and returns a toolset that has its own connection. A word on safety that is ours: the tool descriptions and results of an MCP server are text that your model reads. Connect only to servers you trust, and give a token the fewest rights it needs.

## Capabilities hold the pieces together

You have now met tools, toolsets, delegation and MCP. The [Capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) page names what ties them together. A capability is a reusable unit of agent behaviour. Instead of passing instructions, model settings, toolsets and hooks as separate arguments, you bundle related ones and pass them in `capabilities=[...]`. A capability can provide tools, lifecycle hooks, instructions, model settings and model choice. The page calls capabilities the main extension point of Pydantic AI.

Three of them matter to this lesson.

- The `MCP` capability is the recommended way to attach an MCP server, according to the MCP Client page. It takes a URL, or an `MCPToolset` input through `local=`, and has a `native=True` flag to use the model provider's own MCP support. The page says to reach for `MCPToolset` yourself when you must manage the client's lifecycle, share one server between agents, or pass settings the capability does not offer. We ran it with the in-process server from above: `Agent(..., capabilities=[MCP(local=server)])`. With `TestModel(call_tools=['add'])` the model called the `add` tool and the run finished.
- The `Capability` class bundles instructions and tools without writing a subclass. We ran the docs' idea. A `Capability(id='refunds', description=..., instructions=...)` with a tool added by `@refunds.tool_plain` put both the tool and the instructions into the agent that had `capabilities=[refunds]`. We saw the fake model receive the tool `refund_status` and the instruction text. The page says that adding `defer_loading=True` turns it into an on-demand capability, shown to the model as a one-line catalogue entry until the model loads it. We did not run that.
- `SubAgents`, the Harness capability from the delegation section, appears in the page's table next to Planning and Dynamic Workflow, under "Reasoning, planning & delegation".

The same page lists many more capabilities, such as guardrails, spend limits and durable execution. You do not need them now. Come back when you meet the problem each one solves.

## The task

The task for this lesson is the delegation tool. The starter has a desk agent and a stock agent, and a stub tool `check_stock`. You finish it so the desk agent can ask the stock agent: an `async def`, a call with the shared dependencies and usage, and the delegate's output returned. The hidden tests use `FunctionModel` on both agents. Open `task/README.md` for the steps.

Sources: [Multi-agent Applications](https://pydantic.dev/docs/ai/guides/multi-agent-applications/), [MCP Client](https://pydantic.dev/docs/ai/mcp/client/) and [Capabilities](https://pydantic.dev/docs/ai/capabilities/overview/) from the Pydantic AI documentation, version 2.56.0, MIT licence, © Pydantic Services Inc. 2024 to present. [What is the Model Context Protocol (MCP)?](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro) from the Model Context Protocol documentation, version 2026-07-28, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), adapted: summarised in our own words. This site is not affiliated with Pydantic.
