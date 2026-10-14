---
id: pa2-tools-deps
track: pydantic-ai
title: "Tools and dependencies"
minutes: 30
pins:
  pydantic-ai: "2.56.0"
sources:
  - pydantic-ai-tools-toolsets-tools
  - pydantic-ai-core-concepts-dependencies
  - pydantic-ai-guides-testing
---

A model can only produce text. A tool lets it ask your code to do something, such as look up a price or read a record. In this lesson you give an agent a tool, hand that tool what it needs without globals, let it ask the model to try again, and test all of it without an API key.

## What a tool is

A tool is a plain Python function that you register on an agent. The model never runs it. When the model wants the result, it replies with a tool call: the tool name plus arguments. Your agent runs the function, adds the return value to the message history, and sends the history back to the model. This goes on until the model answers with plain text. [Function Tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/) shows this loop with a dice game.

So who decides whether a tool is called? The model does. Your code only offers the tool. The model picks from what it is shown, and what it is shown is built from your function:

- The function name becomes the tool name.
- The docstring's first lines become the tool description. This is what the model reads to decide when the tool is useful.
- Each parameter becomes part of a JSON schema. A parameter description comes from an `Args:` entry in the docstring.
- The return value must be something Pydantic can turn into JSON. A `float` or a `str` is fine.

```python
@agent.tool_plain
def get_forecast(city: str) -> str:
    """Return the forecast for a city (full name only).

    Args:
        city: The city, spelled out, for example "San Francisco".
    """
    ...
```

A vague or missing docstring means a model that guesses. Write the docstring for the model, not only for people. The same page explains [which docstring parts reach the model](https://pydantic.dev/docs/ai/tools-toolsets/tools/#tool-schema): the description, the parameter descriptions and the first returns entry. Other sections, such as `Raises`, are dropped.

## Choosing the decorator

Pydantic AI has two decorators for registering a tool on an agent, described under [Registering via Decorator](https://pydantic.dev/docs/ai/tools-toolsets/tools/#registering-via-decorator).

- `@agent.tool` is for a function that needs the run context. Its first parameter must be `ctx: RunContext[...]`. This is the default choice.
- `@agent.tool_plain` is for a function that needs nothing from the run. It has no `ctx` parameter.

```python
@agent.tool_plain
def roll_dice() -> str:
    """Roll a six-sided die."""
    return str(random.randint(1, 6))


@agent.tool
def get_player_name(ctx: RunContext[str]) -> str:
    """Get the player's name."""
    return ctx.deps
```

The `ctx` parameter is not part of the schema. The model never sees it and never fills it in. It is how your own code reaches the run, and the next section shows what lives on it. If you start with `tool_plain` and later need data from the run, switch the decorator and add `ctx` as the first parameter.

## Dependencies instead of globals

Most real tools need something: an HTTP client, a database connection, an API key, the id of the current user. The easy way is a module-level global. That works until you want to test the tool or run two users at once. Then the tool reads the wrong data, or it reaches a real service.

Pydantic AI uses dependency injection instead, as explained on the [Dependencies](https://pydantic.dev/docs/ai/core-concepts/dependencies/) page. There are three steps:

1. Put what the tool needs into one object. A dataclass works well when there are several things.
2. Tell the agent the type with `deps_type=`. You pass the class, not an instance. This is only for type checking.
3. Pass an instance when you run the agent, with `deps=`. Inside a tool, read it from `ctx.deps`.

```python
@dataclass
class Deps:
    prices: dict[str, float]


agent = Agent("openai:gpt-5.2", deps_type=Deps)


@agent.tool
def price_of(ctx: RunContext[Deps], item: str) -> float:
    """Return the price of an item."""
    return ctx.deps.prices[item]


result = agent.run_sync("How much is tea?", deps=Deps(prices={"tea": 2.5}))
```

Because `RunContext[Deps]` carries the type, your editor and type checker know that `ctx.deps.prices` exists. You choose the deps for each run, so two users can run side by side with different data. In tests you pass a different `Deps` with fake data. Nothing else changes.

## Asking the model to retry

Models make mistakes. They spell a city as "SF" when your data says "San Francisco". If the tool raises a normal exception, the run crashes. If the tool raises `ModelRetry`, the run keeps going.

```python
from pydantic_ai import ModelRetry


@agent.tool
def get_forecast(ctx: RunContext[Deps], city: str) -> str:
    """Return the forecast for a city (full name only)."""
    if city not in ctx.deps.forecasts:
        raise ModelRetry("City not found, try the full name")
    return ctx.deps.forecasts[city]
```

The message you pass becomes a retry prompt in the history, and the agent makes another request to the model. The model reads the hint and calls the tool again with better arguments. It does not repeat any network call: `ModelRetry` is a conversation with the model, not a retry of HTTP or of your function. The [Dependencies](https://pydantic.dev/docs/ai/core-concepts/dependencies/#full-example) page uses it inside a tool and an output validator.

Write the hint so the model can act on it. "Unknown item, try one of: coffee, tea" helps. "Error" does not. Raise `ModelRetry` for mistakes the model can fix by changing its arguments. Retries are limited. In Pydantic AI 2.56.0 a tool gets one retry by default, and when the model keeps failing the run stops with an `UnexpectedModelBehavior` error. Bugs in your own code, such as a broken database connection, should still raise normal exceptions. The model cannot fix those.

## Testing tools without a key

Calling a real model in a unit test is slow, costs money and gives a different answer each time. The [Unit Testing](https://pydantic.dev/docs/ai/guides/testing/) page lists four tools that avoid this.

- `TestModel` stands in for the model. By default it calls every tool, with made-up arguments that match the schema, and then answers with text. Use it to check that the wiring works.
- `FunctionModel` lets you write the model yourself as a Python function. It gets the message history and an `AgentInfo`, and returns a `ModelResponse`. Use it to script exact behaviour: call the tool with a bad argument first, then with a good one.
- `agent.override(model=..., deps=...)` swaps the model or the deps for the duration of a `with` block. It works even when the agent is called deep inside your app, where you cannot change the call.
- `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False` makes any accidental request to a real model fail loudly.

```python
from pydantic_ai import models
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False


def scripted(
    messages, info: AgentInfo
) -> ModelResponse: ...  # look at messages[-1], return a ToolCallPart or a TextPart


with agent.override(model=FunctionModel(scripted)):
    result = agent.run_sync("How much is tea?", deps=Deps(prices={"tea": 2.5}))
```

Run your tests with the guard on and you can trust that none of them spent a cent.

## Watch it run

The trace below shows a real run of an agent with one tool, `get_forecast`. It was recorded with a scripted `FunctionModel`, so no API key was involved. The tool is called with "SF", which the tool rejects with `ModelRetry`. The model then tries "San Francisco", the tool answers, and the model writes the final answer. Step through it, and answer the two prediction questions before you continue. Try to match each step to a part of this lesson: the tool call, the retry prompt and the final text.

Sources: [Function Tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/), [Dependencies](https://pydantic.dev/docs/ai/core-concepts/dependencies/) and [Unit Testing](https://pydantic.dev/docs/ai/guides/testing/) from the Pydantic AI documentation, version 2.56.0, MIT licence. This site is not affiliated with Pydantic.
