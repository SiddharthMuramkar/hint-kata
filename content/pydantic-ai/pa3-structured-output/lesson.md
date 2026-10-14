---
id: pa3-structured-output
track: pydantic-ai
title: "Structured output in depth"
minutes: 30
pins:
  pydantic-ai: "2.56.0"
sources:
  - pydantic-ai-core-concepts-output
  - pydantic-ai-guides-testing
---

In lesson 1 you gave an agent an `output_type` and got an object back. This lesson looks under that one argument. You will see how the model is made to produce the shape you asked for, how to choose between the ways of doing it, how to accept more than one shape, and how to reject an answer that has the right shape but the wrong content. At the end you test all of it without an API key.

## Why structured output

A string is something a person reads. A `Ticket` object is something your code can act on. If an agent triages support mail, you want `ticket.priority` to be an `int` you can sort by, and `ticket.category` to be one of a few known values you can route on. Parsing that out of free text with a regex is fragile: the model changes a word and the parser breaks.

With `output_type`, the [Output page](https://pydantic.dev/docs/ai/core-concepts/output/#structured-output) describes the idea like this: Pydantic builds a JSON schema from your type, the model is asked to answer in that shape, and Pydantic validates the answer. The type can be a Pydantic model, a dataclass, a `TypedDict`, a scalar such as `int`, a `list`, or a union of these. What you get in `result.output` is already a real Python value, and the agent's type parameter carries the type to your editor.

```python
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent


class Ticket(BaseModel):
    category: Literal["bug", "billing", "other"]
    priority: int
    summary: str


agent = Agent("openrouter:anthropic/claude-haiku-5.5", output_type=Ticket)
result = agent.run_sync("The invoice PDF will not open, please help!")
ticket = result.output  # a Ticket, not a string
```

Two things follow. First, when the output type is not a plain string, the model is not allowed to simply chat: the run only ends when the model produces a value of that type. Second, a model can still get the content wrong. A `Literal` stops "banana" from being a category, but it cannot know that priority 9 makes no sense in your system. Later sections show where that kind of rule goes.

## Output modes

The model is a text generator. So how does Pydantic AI make it hand back a structured object? There are three methods, which the Output page calls [output modes](https://pydantic.dev/docs/ai/core-concepts/output/#output-modes), plus one close relative for plain text.

- **Tool output** is the default. Your schema is shown to the model as the parameters of a special output tool. To answer, the model calls that tool. Pydantic validates the arguments, and that is your output. Almost every model supports tool calling, and the docs say it has worked very well, so it is the safe default.
- **Native output** uses the model API's own structured output feature, sometimes called a JSON schema response format. The API forces the model's text reply to match the schema. It is not available on every model, and it can come with restrictions. The docs give an example: an earlier Gemini model cannot combine native output with function tools.
- **Prompted output** writes the schema into the instructions and asks nicely. The model may ignore it. It works with every model, is often the least reliable, and is the only choice for a model that has neither tool calling nor structured output. Pydantic AI still validates the reply and asks again if it is wrong.
- **Text output** is for when you want plain text in, and a function of yours turning that text into the final value, with `TextOutput(my_function)`.

You choose a mode by wrapping the type in a marker class. The classes are `ToolOutput`, `NativeOutput`, `PromptedOutput` and `TextOutput`, all importable from `pydantic_ai`:

```python
from pydantic_ai import Agent, NativeOutput, PromptedOutput, ToolOutput

Agent(model, output_type=Ticket)  # tool output, the default
Agent(model, output_type=ToolOutput(Ticket, name="file_ticket"))
Agent(model, output_type=NativeOutput(Ticket))  # the API enforces the schema
Agent(model, output_type=PromptedOutput(Ticket))  # the schema goes in the instructions
```

The three structured markers (`ToolOutput`, `NativeOutput` and `PromptedOutput`) also take a `name` and a `description` where the docstring of your type is not enough. Writing `output_type=Ticket` and wrapping it in `ToolOutput` look the same to the model unless you need those extras.

How do you pick? Start with the default. Move to `NativeOutput` when the model and provider support it and you want the API itself to hold the model to the schema. Use `PromptedOutput` when nothing else is available or when the docs for your model tell you it gives better quality that way. You can check what you chose in a test: a `FunctionModel` sees `info.model_request_parameters.output_mode`, which reads `tool`, `native` or `prompted`.

One more point about the default, stated for the installed version only, because the Output page does not cover it. Tool output forces the model to call the output tool, and for some models a forced tool call stops them from thinking first. In Pydantic AI 2.56.0 the default is therefore swapped from tool to native output when three things hold: the model's profile says a forced tool choice blocks or disables thinking, the request is going to think, and the model supports JSON schema output. This is true for every Anthropic model, and the Claude 5.x family thinks by default, so a plain `output_type=Ticket` on one of them is sent in native mode. I checked the rule with a `FunctionModel` whose profile sets those three flags: its request had `output_mode == "native"`, and it went back to `"tool"` when any one flag was missing. On top of that, the Anthropic adapter handles extended thinking with a fixed budget, which rejects forced tool choice outright: there the default becomes native if the model supports JSON schema output, and prompted if it does not. If you rely on any of this, check the installed version's source or release notes, because it can change between versions.

## Unions and output functions

Sometimes there is more than one valid answer. A triage agent may return a `Ticket`, or ask a question back because the message was unclear. Pass a union or a list as `output_type`:

```python
class Question(BaseModel):
    text: str


agent = Agent(model, output_type=[Ticket, Question])  # or Ticket | Question
```

Each member becomes its own output tool, so the model chooses the shape by choosing which tool to call. The [Output page](https://pydantic.dev/docs/ai/core-concepts/output/#structured-output) says this keeps each schema small and makes a correct answer more likely, compared with one giant combined schema. If you add `str` to the list, a plain text reply also ends the run. Then your code checks which kind came back with `isinstance`. If you pass a list or a union, a type checker such as mypy may need help with the type parameters of `Agent`, and the page explains when.

If your code would then branch on the result anyway, there is a shorter way: an [output function](https://pydantic.dev/docs/ai/core-concepts/output/#output-functions). You pass a function as the output type. The model is forced to call it, Pydantic validates the arguments the same way as for tools, and what the function returns becomes the run's result.

```python
def create_ticket(category: str, summary: str) -> Ticket:
    """File a ticket in the helpdesk."""
    ...


agent = Agent(model, output_type=[create_ticket, Question])
```

This looks like a tool, and there is one difference that matters. A tool's return value goes back to the model, which goes on. An output function's return value ends the run and is not sent back. Like a tool, it may take `ctx: RunContext[...]` first and may raise `ModelRetry` to send the model back for another try. You usually do not want to register the same function as a tool as well, because the model may be unsure which one to call. And with streaming, an output function is called once per partial output, so check `ctx.partial_output` before side effects such as sending an email. The streaming section returns to this.

## Output validators and ModelRetry

Pydantic checks types. Your business rules need code. "Priority must be between 1 and 5" and "the summary must fit the helpdesk's 120 character field" are examples. You can put these in a Pydantic validator on the model, but sometimes they need IO, such as a database lookup, or a rule that depends on the run. For those, register an output validator with the [`@agent.output_validator`](https://pydantic.dev/docs/ai/core-concepts/output/#output-validators) decorator. It receives the output after Pydantic accepted its shape. It returns the output, possibly changed, or raises `ModelRetry`:

```python
from pydantic_ai import ModelRetry

agent = Agent(model, output_type=Ticket)


@agent.output_validator
def check_ticket(ticket: Ticket) -> Ticket:
    if not 1 <= ticket.priority <= 5:
        raise ModelRetry("priority must be a whole number from 1 to 5")
    return ticket
```

The validator may also take `ctx: RunContext[...]` as its first parameter, for example to reach `ctx.deps`. When `ModelRetry` is raised, its message goes back to the model as a retry prompt, and the model answers again. This is the same mechanism you met for tools in lesson 2. If the model's answer does not even match the schema, for example a priority of "high", Pydantic produces a retry prompt on its own, with the details of what was wrong. So the model gets feedback in both cases.

The loop is not endless. It has a budget. In Pydantic AI 2.56.0 the output retry budget defaults to 1, and each `ModelRetry` from an output validator uses one unit, as the Output page says. A Pydantic validation failure also needs a retry, and in a scripted run with a `FunctionModel`, two validation failures in a row with the default budget ended the run. With a union, each output tool has its own retry counter, and the budget is the default limit for each one. You change the budget on the agent with `Agent(..., retries={"output": 3})`, or for a single run with `agent.run(..., retries={"output": 3})`. When the budget runs out, the run raises `UnexpectedModelBehavior` with a message like "Exceeded maximum output retries (1)". Plan for that error. It is how you find out a model cannot meet your rule, and a bigger budget is not always the fix: a better message, a clearer instruction or a different model might be.

Write the message for the model, as with tools. "Invalid" tells it nothing. "priority must be a whole number from 1 to 5" tells it what to change. Put a hard rule in a validator only if the model can meet it by trying again. If a field is only ever filled from something the model cannot know, retrying will not help.

## Streaming partial output

For a long structured answer, waiting for the full reply makes an app feel slow. Use `agent.run_stream()` and read `result.stream_output()`. The model's reply is validated while it is still arriving, which Pydantic calls partial validation, and each value you receive is a snapshot of everything so far. Fields that are not complete yet may be missing, so redraw from each snapshot and do not append to what you already have. Pass `debounce_by=None` to get every chunk without waiting.

```python
async with agent.run_stream("Triage this email: ...") as result:
    async for snapshot in result.stream_output():
        show(snapshot)  # a growing, partly filled Ticket
```

There are two things to remember. Output validators run on each snapshot, and once more on the final output. In a scripted stream, the validator was called with `ctx.partial_output` set to `True` for the snapshot and `False` for the last one. Check that flag when a rule only makes sense for a finished answer. Check it in output functions too, before any side effect. Also, `run_stream()` treats the first matching output as final and stops, so tool calls the model makes after it are not run. The [streaming section](https://pydantic.dev/docs/ai/core-concepts/output/#streamed-results) covers `run_stream_events()` and `iter()` for the full picture, and says that tool output needs a model that streams tool arguments.

## Testing structured output without a key

You met `TestModel`, `FunctionModel` and `ALLOW_MODEL_REQUESTS` in lesson 2, and they work the same here. `TestModel` makes up a value that fits your type, so a call with it proves the wiring: the agent builds, and the type is accepted. But the invented values can fail your own validator, for example a priority of 0, so for anything with rules, script a `FunctionModel` instead. The [Unit Testing](https://pydantic.dev/docs/ai/guides/testing/) page describes both. Your `FunctionModel` function receives an `AgentInfo`. In tool output mode the output tools are in `info.output_tools`, and returning a `ToolCallPart` for one of them is how a scripted model gives its answer:

```python
from pydantic_ai import models
from pydantic_ai.messages import ModelResponse, RetryPromptPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False
answers = iter(
    [
        {"category": "bug", "priority": 9, "summary": "x"},
        {"category": "bug", "priority": 3, "summary": "x"},
    ]
)


def scripted(messages, info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, next(answers))])


result = agent.run_sync("hi", model=FunctionModel(scripted))
retries = [p for m in result.all_messages() for p in m.parts if isinstance(p, RetryPromptPart)]
```

The first answer is invalid, so your validator rejects it. The second is valid, so the run succeeds. A `RetryPromptPart` in the message history is the evidence that the retry happened, and its `content` holds your `ModelRetry` message. If the validator fails to run, `retries` is empty. If the model answers wrongly forever, the run raises `UnexpectedModelBehavior`, and a test can assert that too with `pytest.raises`.

That is the whole kit for the task. You write a `Ticket` and an agent whose validator turns bad priorities and long summaries into retries. The hidden tests play the model, so no key or network is needed.

Sources: [Output](https://pydantic.dev/docs/ai/core-concepts/output/) and [Unit Testing](https://pydantic.dev/docs/ai/guides/testing/) from the Pydantic AI documentation, version 2.56.0, MIT licence. © Pydantic Services Inc. 2024 to present. The remark on how thinking changes the default output mode comes from the installed 2.56.0 source code, not from these pages. This site is not affiliated with Pydantic.
