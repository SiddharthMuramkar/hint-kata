---
id: pa1-first-agent
track: pydantic-ai
title: "Your first agent"
minutes: 25
pins:
  pydantic-ai: "2.56.0"
sources:
  - pydantic-ai-overview-install
  - pydantic-ai-core-concepts-agent
  - pydantic-ai-core-concepts-output
  - pydantic-ai-models-overview
---

## What an agent is

An agent is a small object that holds everything you need to talk to a language model in a repeatable way. You build it once. You call it many times. Think of it like a small FastAPI app: one object, reused everywhere.

An `Agent` bundles four main things:

- **A model.** Which LLM answers the questions.
- **Instructions.** Text you write that tells the model how to behave.
- **An output type.** The shape of the answer you want back. It can be plain text or a Pydantic model.
- **Tools.** Python functions the model may call to get more information. We meet tools in a later lesson.

There are a few more parts (dependencies, model settings, capabilities). You can ignore them for now. Only the first three matter today.

The smallest agent has just a model:

```python
from pydantic_ai import Agent

agent = Agent("openrouter:anthropic/claude-haiku-5.5")
result = agent.run_sync("What is the capital of Italy?")
print(result.output)
```

The agent sends your prompt to the model and hands back a result object. The answer lives in `result.output`. Here it is a plain string, because we did not ask for anything else.

In your own project, installing the library is one line: `uv add pydantic-ai` (or `pip install pydantic-ai`). It needs Python 3.11 or newer. This repo already has the slim package with the OpenRouter extra installed.

Read more: [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/) and [Installation](https://pydantic.dev/docs/ai/overview/install/).

## Model strings and providers

You pick the model with a string. The string always has two parts: a **provider**, a colon, and a **model name**.

```text
openrouter:anthropic/claude-haiku-5.5
└─ provider └─ model name (OpenRouter writes it as vendor/model)
```

The provider tells Pydantic AI which service to call and how to log in. The model name tells that service which model to run. Pydantic AI then picks the right model class and settings for you.

Always include the provider prefix. If you write `Agent("gpt-5")`, Pydantic AI does not guess. It raises a `UserError` that says the model is unknown, and it suggests a prefixed name.

Hint Kata uses **OpenRouter**. One OpenRouter key gives you access to models from many vendors, so you can swap models by changing a string. Other prefixes you will see are `openai:`, `anthropic:` and `google:`.

The key never goes in your code. Put it in `.env` as `OPENROUTER_API_KEY`. Pydantic AI reads the key from the environment when it builds the model. If the variable is missing, creating the agent fails right away with a `UserError` that names the variable. That is a helpful early error. Nothing has been sent to the network yet.

A script you run yourself does not read `.env` on its own. Load it into your shell first, or export the variable by hand.

You can also override the model for a single call. Pass `model=` to `run_sync` or `run`. This is handy in tests, as you will see in the task.

Read more: [Models and Providers](https://pydantic.dev/docs/ai/models/overview/).

## Instructions, not system prompts

Both `instructions` and `system_prompt` are text the model sees before your question. Pydantic AI supports both. The docs recommend `instructions` for almost everything.

The difference shows up when you continue a conversation. You can pass earlier messages back in with `message_history`.

- With `system_prompt`, the old system prompt stays in the history and is sent again.
- With `instructions`, only the **current** agent's instructions are sent. Instructions stored in older messages are left out.

So `instructions` always reflect the agent you are running right now. If you change them in code, the next call uses the new text. There is no stale copy hiding in the history. This also makes it safe to hand a conversation from one agent to another.

Instructions are not a one-time setup. They go out with each request. Keep them short and specific.

Good instructions say what to do and what to avoid. Compare these two:

```python
# vague
Agent(model, instructions="Be helpful.")

# clear
Agent(
    model,
    instructions=(
        "You answer questions about cities. "
        "Be concise: two sentences at most. "
        "If you are not sure of a number, say so instead of guessing."
    ),
)
```

The second one gives the model a role, a length limit and a rule for uncertainty. You can check each of those by reading the output.

When the text depends on something only known at run time, such as the user's name, use an `@agent.instructions` function. It runs on every call. We cover that when we reach dependencies.

Read more: the [Instructions](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions) and [System Prompts](https://pydantic.dev/docs/ai/core-concepts/agent/#system-prompts) sections of the Agents page.

## Running an agent

The two ways you will use most are `run_sync` and `run`.

```python
# In a plain script: blocks until the answer arrives.
result = agent.run_sync("Tell me about Lisbon.")

# Inside async code, such as a FastAPI endpoint: await it.
result = await agent.run("Tell me about Lisbon.")
```

They do the same work. `run_sync` is a normal function. `run` is a coroutine, so you `await` it. Use `run` in async code. Calling `run_sync` from inside a running event loop is a mistake.

There are more ways to run an agent: `run_stream` for streaming text, `run_stream_events` for a stream of events, and `iter` for stepping through the run node by node. They come later.

Whichever you call, you get back a result object. Two attributes matter now:

- `result.output` is the final value. Its type follows the agent's `output_type`.
- `result.usage` tells you what the run cost in tokens and requests. In Pydantic AI 2 it is a **property**, not a method. Write `result.usage`, not `result.usage()`.

```python
print(result.output)
print(result.usage)
# > RunUsage(input_tokens=57, output_tokens=8, requests=1)
```

A single call is one **run**. A run can contain several requests to the model, for example when tools are involved. A longer chat is a **conversation**, made of several runs. To continue one, pass the earlier messages into the next call. Each run starts with a fresh set of instructions from the current agent.

Read more: the [Running Agents](https://pydantic.dev/docs/ai/core-concepts/agent/#running-agents) and [Runs vs. Conversations](https://pydantic.dev/docs/ai/core-concepts/agent/#runs-vs-conversations) sections of the Agents page.

## Structured output with a Pydantic model

By default the answer is text. Text is hard to use in code. You end up parsing strings with regexes. Small changes in the model's wording then break your program.

The fix is `output_type`. Give the agent a Pydantic model and it must return data that fits it:

```python
from pydantic import BaseModel, Field


class CityLocation(BaseModel):
    city: str
    country: str
    population: int = Field(description="Approximate number of people")


agent = Agent(
    "openrouter:anthropic/claude-haiku-5.5",
    output_type=CityLocation,
)
result = agent.run_sync("Where were the 2012 Olympics held?")
print(result.output.city)  # a real attribute, not a string to parse
```

This is better than parsing text for four reasons:

1. **Validated.** Pydantic checks the data. A population that is not a number is rejected. Pydantic AI then asks the model to try again.
2. **Typed.** `result.output` is a `CityLocation`. Your editor and type checker know it has `.city`.
3. **Described.** The model sees your field names and `Field(description=...)` text, so the schema also guides it.
4. **Stable.** Your code reads fields. It does not care how the model phrases things.

How does the model return structured data? By default Pydantic AI registers a special **output tool** built from your model's JSON schema. The model "calls" it to give the final answer. There are two other modes: **native output**, where the provider forces JSON that matches the schema, and **prompted output**, where the schema is added to the instructions as text. You rarely need to choose. In the installed version (2.56.0), for some reasoning models a forced tool call would switch their thinking off, so Pydantic AI falls back to native JSON output when the model supports it.

You can also allow more than one outcome with a list: `output_type=[CityLocation, str]`. The model can then return a city, or plain text to ask a follow-up question.

Read more: the [Output](https://pydantic.dev/docs/ai/core-concepts/output/) page, especially [Structured output data](https://pydantic.dev/docs/ai/core-concepts/output/#structured-output-data) and [Output modes](https://pydantic.dev/docs/ai/core-concepts/output/#output-modes).

## Try it yourself

Here is a complete agent with instructions and a structured output. Save it as `movie.py`:

```python
from pydantic import BaseModel
from pydantic_ai import Agent


class Movie(BaseModel):
    title: str
    year: int


agent = Agent(
    "openrouter:anthropic/claude-haiku-5.5",
    instructions="Name one well-known film that fits the description. Be concise.",
    output_type=Movie,
)
result = agent.run_sync("A shark terrorises a beach town.")
print(result.output)
print(result.usage)
```

Make sure `OPENROUTER_API_KEY` is set in your shell, then run it with `uv run python movie.py`. This one call goes to the network and costs a tiny amount.

Things to try:

- Change the description and watch `result.output` change. It is always a `Movie`.
- Add a field such as `director: str`. The model fills it in with no other change.
- Remove `output_type` and print `result.output`. It is now a plain string.
- Change the model string to just `"gpt-5"`. You will see the `UserError` from the model strings section.

The hands-on task after the quiz builds a similar agent. It uses a `TestModel`, so its checks need no key and no network.

---

Sources: [Installation](https://pydantic.dev/docs/ai/overview/install/), [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/), [Output](https://pydantic.dev/docs/ai/core-concepts/output/), [Models Overview](https://pydantic.dev/docs/ai/models/overview/).
