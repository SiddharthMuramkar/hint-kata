---
id: pa9-testing-agents
track: pydantic-ai
title: "Testing agents"
minutes: 30
pins:
  pydantic-ai: "2.56.0"
  pytest: "9.1"
sources:
  - pydantic-ai-guides-testing
  - pydantic-ai-core-concepts-agent
  - pydantic-ai-core-concepts-retries
  - pydantic-ai-tools-toolsets-tools
---

A good test is fast, free and the same on every run. A real model is none of these. So you test an agent with a fake model, and you check what the agent did, not only what it said. In this lesson you block real requests, use `TestModel` and `FunctionModel`, swap the model for one test, read the exact messages of a run, check tool order and arguments, script retries, and check usage. Last, you see how this site tests its own tutor and grader. We ran every example on Pydantic AI 2.56.0 and pytest 9.1. Where a point comes only from the docs, the text says so.

## Why a test must never call a real model

A real model call has three problems in a test. It costs money. It is slow. And it answers differently from run to run, so a test that passes today can fail tomorrow. The [Unit Testing](https://pydantic.dev/docs/ai/guides/testing/) guide gives a plan: use `pytest`, put a fake model in place of the real one, and block real requests for the whole test run.

The block is two lines:

```python
# conftest.py
from pydantic_ai import models

models.ALLOW_MODEL_REQUESTS = False
```

Put it in `conftest.py` at the top of your tests folder. pytest loads that file before it runs any test, so the flag is set early. This site does the same in `tests/conftest.py`.

Real models check the flag before they send a request. When it is `False`, they raise `RuntimeError`. The docs say it blocks requests to non-test models, and we saw that `TestModel` and `FunctionModel` still run with the flag off. See [`ALLOW_MODEL_REQUESTS`](https://pydantic.dev/docs/ai/api/models/base/#pydantic_ai.models.ALLOW_MODEL_REQUESTS) in the API reference.

One more thing we saw. We used an agent that names the model `openai:gpt-5.2`, and we ran it with no override.

- With no API key in the environment, the run raised `UserError` about the missing key. The key check comes before the flag check.
- With a made-up key in the environment, the flag fired: `Model requests are not allowed, since ALLOW_MODEL_REQUESTS is False`.

So the flag matters most on a laptop that has a real key. That is exactly the machine where a forgotten override would cost money.

## The agent under test

All the examples below test this small shop agent. It has two tools and a structured answer.

```python
# shop.py
from dataclasses import dataclass

from pydantic import BaseModel
from pydantic_ai import Agent, ModelRetry, RunContext


@dataclass
class ShopDeps:
    prices: dict[str, float]


class Quote(BaseModel):
    item: str
    total: float


shop_agent = Agent(
    "openai:gpt-5.2",
    deps_type=ShopDeps,
    output_type=Quote,
    instructions="Quote the price of an item with tax. Use price_of, then add_tax.",
    defer_model_check=True,
)


@shop_agent.tool
def price_of(ctx: RunContext[ShopDeps], item: str) -> float:
    """Return the price of an item, before tax."""
    if item not in ctx.deps.prices:
        raise ModelRetry(f"Unknown item {item!r}. Try one of: {', '.join(ctx.deps.prices)}")
    return ctx.deps.prices[item]


@shop_agent.tool_plain
def add_tax(price: float) -> float:
    """Add 20% tax to a price."""
    return round(price * 1.2, 2)
```

The `price_of` tool reads its prices from the dependencies and asks the model to retry on an unknown item. You met both ideas in the lesson on tools and dependencies. The argument `defer_model_check=True` is explained in the section on `override`.

## Fast guesses with TestModel

`TestModel` is a fake model that needs no script. By default it calls every tool once, then answers. The docs stress that it contains no AI. It is plain code that makes data to fit the JSON schema of each tool and of the output type. The data will not look sensible, but it should pass validation.

```python
from pydantic_ai.models.test import TestModel


def test_testmodel() -> None:
    deps = ShopDeps(prices={"a": 2.5})
    with shop_agent.override(model=TestModel()):
        result = shop_agent.run_sync("How much is tea?", deps=deps)
    assert result.output == Quote(item="a", total=0.0)
```

Why the key `"a"`? We saw that `TestModel` makes up the values of the arguments. A string became `"a"` and a number became `0.0`. So it called `price_of("a")` and `add_tax(0.0)`, and the structured answer was `Quote(item='a', total=0.0)`. It put both tool calls in its first reply, in the order the tools were registered.

With `prices={"tea": 2.5}` the same test failed. `price_of("a")` raised `ModelRetry`, `TestModel` sent `"a"` again, and the run raised `UnexpectedModelBehavior` because the tool had used up its one retry. So with `TestModel` you must shape your test data to match what it invents. If you cannot, use `FunctionModel`.

`TestModel` has a few settings. We ran two of them.

- `call_tools=["price_of"]` calls only the listed tools. The default is all of them.
- `custom_output_args={"item": "tea", "total": 3.0}` sets the structured answer. For a plain-text agent, `custom_output_text="..."` sets the text. This site uses it for the tutor.

Use `TestModel` for smoke tests, for wiring, and for testing the code around the agent. The docs add one limit: it cannot act as a provider-run native tool. If your agent has those, the docs say to override them with `native_tools=[]` in tests.

## Scripted replies with FunctionModel

`FunctionModel` runs your function in place of a model. The function gets the `messages` so far and an `AgentInfo`. It returns a `ModelResponse`. So you write the model's side of the chat.

```python
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel


def script(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    returns = [p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)]
    if not returns:
        return ModelResponse(parts=[ToolCallPart("price_of", {"item": "tea"})])
    if returns[-1].tool_name == "price_of":
        return ModelResponse(parts=[ToolCallPart("add_tax", {"price": returns[-1].content})])
    return ModelResponse(
        parts=[ToolCallPart("final_result", {"item": "tea", "total": returns[-1].content})]
    )


def test_scripted_quote() -> None:
    deps = ShopDeps(prices={"tea": 2.5})
    with shop_agent.override(model=FunctionModel(script)):
        result = shop_agent.run_sync("How much is tea?", deps=deps)
    assert result.output == Quote(item="tea", total=3.0)
```

The function is called once per request. In this run it was called three times: first to ask for the price, then to add tax, then to answer. The script reads the history to know where it is. It looks at the `ToolReturnPart` objects.

The structured answer comes back as a tool call named `final_result`. That is the name we saw for the output tool of a structured agent.

The `info` argument tells you what the agent offers the model. In our run `info.function_tools` listed `price_of` and `add_tax`, `info.output_tools` listed `final_result`, and `info.allow_text_output` was `False`. The agent's instructions were on the first request, as `messages[0].instructions`. So a `FunctionModel` can also check that the model was given the right tools and instructions. The [guide](https://pydantic.dev/docs/ai/guides/testing/#unit-testing-with-functionmodel) shows a script that reads the user prompt and builds the tool arguments from it.

A script often needs memory. A simple way is a list of replies and `next()`. You will see that in the retry section. The docs also say that `FunctionModel` accepts a callable object with an `async def __call__`, for a model that must keep state between requests.

## Swapping the model with override

`agent.override(model=...)` is a context manager. Inside the `with` block, every run of that agent uses the fake model. This works even when the run happens deep inside your app code, so you do not need to pass a model to every call. That is the main point the guide makes about it.

`override` takes other arguments too. We ran `deps=`:

```python
with shop_agent.override(model=TestModel(), deps=ShopDeps(prices={"a": 1.0})):
    result = shop_agent.run_sync("hi")  # no deps= here
```

If many tests need the same fake, put the `with` in a pytest fixture and `yield` inside it:

```python
import pytest


@pytest.fixture
def fake_shop():
    with shop_agent.override(model=TestModel(call_tools=[])):
        yield


def test_with_fixture(fake_shop: None) -> None:
    result = shop_agent.run_sync("How much is tea?", deps=ShopDeps(prices={}))
    assert result.output == Quote(item="a", total=0.0)
```

The examples use `run_sync`. If the code under test is async, the guide marks the test module with `pytestmark = pytest.mark.anyio` and awaits `agent.run(...)`. We ran a test that way. The pytest plugin comes with anyio, which is already installed in this project, and it loaded by itself.

Now the argument `defer_model_check=True`. When you name a model with a string, Pydantic AI builds the model object as soon as the `Agent` is created, and that checks for the API key. We saw `Agent("openai:gpt-5.2")` raise `UserError` at that moment when no key was set. That would break every test file that imports the agent, before any override can run. With `defer_model_check=True` the check waits until the first run. The [Agent reference](https://pydantic.dev/docs/ai/api/pydantic-ai/agent/) describes it, and says it helps when you override the model in tests. The tutor on this site is built with it.

## Reading the run with capture_run_messages

`override` swaps the model. It does not show you what happened. `capture_run_messages()` does. Run the agent inside it and you get the list of messages of the run. The guide says to use it to assert that the exchange between agent and model went as expected.

```python
from pydantic_ai import capture_run_messages


def test_messages() -> None:
    deps = ShopDeps(prices={"tea": 2.5})
    with capture_run_messages() as messages:
        with shop_agent.override(model=FunctionModel(script)):
            shop_agent.run_sync("How much is tea?", deps=deps)
    assert len(messages) == 7
```

For the scripted run the list had seven messages. Requests and responses took turns:

1. a `ModelRequest` with the user prompt,
2. a `ModelResponse` with the call to `price_of`,
3. a `ModelRequest` with the tool return,
4. a `ModelResponse` with the call to `add_tax`,
5. a `ModelRequest` with the tool return,
6. a `ModelResponse` with the call to `final_result`,
7. a `ModelRequest` with a tool return whose content is `Final result processed.`

In this run the captured list was equal to `result.all_messages()`. The captured list is also what you have when the run fails. The docs use it that way for model errors. In a run that raised `UnexpectedModelBehavior` we still got five messages, and the last one was an empty `ModelRequest` with `state='interrupted'`. The docs describe that state too.

One rule from the docs: if you start more than one run inside one `capture_run_messages` block, you only get the first run. We saw the same with two `run_sync` calls.

Messages carry timestamps and run ids, so comparing a whole list with `==` is hard. Often you do not need the whole list, only the tool calls. The next section does that. The section on dirty-equals shows how to compare a whole list.

## Asserting tool order and arguments

A final answer can be right when the agent got there the wrong way. It might skip a lookup, or call a tool with the wrong argument. So assert the calls themselves. They are the `ToolCallPart` objects inside the `ModelResponse` messages.

```python
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart


def tool_calls(messages: list[ModelMessage]) -> list[tuple[str, dict]]:
    return [
        (part.tool_name, part.args_as_dict())
        for message in messages
        if isinstance(message, ModelResponse)
        for part in message.parts
        if isinstance(part, ToolCallPart) and part.tool_name != "final_result"
    ]


def test_tool_order() -> None:
    deps = ShopDeps(prices={"tea": 2.5})
    with capture_run_messages() as messages:
        with shop_agent.override(model=FunctionModel(script)):
            shop_agent.run_sync("How much is tea?", deps=deps)
    assert tool_calls(messages) == [("price_of", {"item": "tea"}), ("add_tax", {"price": 2.5})]
```

We skip `final_result`, because it is the answer and not one of your tools. We use `args_as_dict()` because a real model gives the arguments as a JSON string, while a script may give a dict. The method returns a dict for both.

With `TestModel` the same helper gave `[("price_of", {"item": "a"}), ("add_tax", {"price": 0.0})]`. The order was the order in which the tools were registered. That makes `TestModel` a cheap way to pin the order. If someone moves a tool in the file, the test fails. Do not assert on `tool_call_id`. `TestModel` builds it from the tool name, and a real model makes its own.

Keep one detail in mind. The list shows the order the model **asked** for the calls. It is not the order they **finished**. We built an agent whose model asks for a slow tool and then a fast tool in one reply. By default the fast one finished first. With `sequential=True` on the tools, the slow one ran and finished first. So if one tool needs the side effect of another, as `refund` needs `lookup_order` in this lesson's task, mark them `sequential=True` and test the order. The [Tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/) page covers the decorators.

## Scripting retries

When a tool raises `ModelRetry`, the agent sends the message back to the model as a `RetryPromptPart`, and the model tries again. The [Retries](https://pydantic.dev/docs/ai/core-concepts/retries/#tool-retries) page documents the rules. The default budget is one retry for each tool. The count is kept per tool name and is cleared when that tool succeeds. When a tool uses up its budget, the run raises `UnexpectedModelBehavior`.

With `FunctionModel` you script both sides: a bad call, then a good one.

```python
from pydantic_ai.messages import ModelRequest, RetryPromptPart


def test_retry_then_recover() -> None:
    replies = iter(
        [
            ModelResponse(parts=[ToolCallPart("price_of", {"item": "teaa"})]),
            ModelResponse(parts=[ToolCallPart("price_of", {"item": "tea"})]),
            ModelResponse(parts=[ToolCallPart("final_result", {"item": "tea", "total": 2.5})]),
        ]
    )
    model = FunctionModel(lambda messages, info: next(replies))
    with capture_run_messages() as messages:
        with shop_agent.override(model=model):
            result = shop_agent.run_sync("How much is tea?", deps=ShopDeps(prices={"tea": 2.5}))
    (retry,) = [
        part
        for message in messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, RetryPromptPart)
    ]
    assert retry.tool_name == "price_of"
    assert retry.content == "Unknown item 'teaa'. Try one of: tea"
    assert result.output == Quote(item="tea", total=2.5)
```

The retry prompt took the place of the tool return for that call. Its `content` is the text you gave to `ModelRetry`. The model sees that text with `Fix the errors and try again.` added; you get the full text from `retry.model_response()`. The docs show the same shape in [What a retry looks like in message history](https://pydantic.dev/docs/ai/core-concepts/retries/#what-a-retry-looks-like-in-message-history).

To test the other end, script a model that never gets it right. The run must fail:

```python
from pydantic_ai.exceptions import UnexpectedModelBehavior


def test_retry_budget_is_used_up() -> None:
    bad = ModelResponse(parts=[ToolCallPart("price_of", {"item": "teaa"})])
    replies = iter([bad, bad])
    model = FunctionModel(lambda messages, info: next(replies))
    with pytest.raises(UnexpectedModelBehavior, match="price_of"):
        with shop_agent.override(model=model):
            shop_agent.run_sync("How much is tea?", deps=ShopDeps(prices={"tea": 2.5}))
```

A scripted model is also the way to test a loop guard. We scripted a model that asks for the same tool forever and ran it with `usage_limits=UsageLimits(request_limit=3)`. The run raised `UsageLimitExceeded`. The [usage limits](https://pydantic.dev/docs/ai/core-concepts/agent/#usage-limits) section of the Agents page explains the options.

## Asserting usage

`result.usage` holds the usage of the run. In 2.56.0 it is a property, so write it without parentheses. We called it as a method and got `TypeError: 'RunUsage' object is not callable`. The [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/#accessing-usage-and-final-output) page describes the `RunUsage` object. Two of its fields are easy to assert: `requests` and `tool_calls`.

```python
def test_usage() -> None:
    deps = ShopDeps(prices={"tea": 2.5})
    with shop_agent.override(model=FunctionModel(script)):
        result = shop_agent.run_sync("How much is tea?", deps=deps)
    assert result.usage.requests == 3  # price_of, add_tax, answer
    assert result.usage.tool_calls == 2
```

The docs say `requests` counts the model responses the agent acts on, one per turn. In our runs:

- the scripted quote gave `requests=3` and `tool_calls=2`,
- the `TestModel` run gave `requests=2` and `tool_calls=2`, because it asked for both tools in one reply,
- the retry run gave `requests=3` and `tool_calls=1`. The call that raised `ModelRetry` was not counted, and the answer was not counted as a tool call.

Why assert usage? It catches an agent that starts to take more turns than it should. Assert `requests` and `tool_calls`. Do not pin the token counts. With a fake model they come from the fake, not from a real tokenizer, so they say little.

## Snapshots and dirty-equals

Messages hold ids and timestamps that change on every run. A long `==` against a list of messages needs a way to say "any string here" or "about now". The guide names two helpers for long assertions.

- [dirty-equals](https://dirty-equals.helpmanual.io/latest/) gives you values that compare equal to a kind of data: `IsStr()`, `IsNow()`, `IsInstance(...)` and more.
- [inline-snapshot](https://15r10nk.github.io/inline-snapshot/latest/) can write the expected value into your test file for you, so you do not type a long assertion by hand. The guide recommends it. We did not run it.

We ran dirty-equals (version 0.11) with `uv run --with dirty-equals`:

```python
from datetime import UTC

from dirty_equals import IsInstance, IsNow, IsStr
from pydantic_ai import RequestUsage
from pydantic_ai.messages import UserPromptPart


def test_first_exchange() -> None:
    with capture_run_messages() as messages:
        with shop_agent.override(model=TestModel(call_tools=["price_of"])):
            shop_agent.run_sync("How much is tea?", deps=ShopDeps(prices={"a": 2.5}))
    assert messages[:2] == [
        ModelRequest(
            parts=[UserPromptPart(content="How much is tea?", timestamp=IsNow(tz=UTC))],
            instructions="Quote the price of an item with tax. Use price_of, then add_tax.",
            timestamp=IsNow(tz=UTC),
            run_id=IsStr(),
            conversation_id=IsStr(),
        ),
        ModelResponse(
            parts=[ToolCallPart(tool_name="price_of", args={"item": "a"}, tool_call_id=IsStr())],
            usage=IsInstance(RequestUsage),
            model_name="test",
            timestamp=IsNow(tz=UTC),
            provider_name="test",
            run_id=IsStr(),
            conversation_id=IsStr(),
        ),
    ]
```

This site does not use either helper. Neither is in `pyproject.toml`, and no test imports them. Its tests check the few fields that matter, which is often the simpler choice.

## How this site tests its tutor and grader

This site is built with Pydantic AI, so its tests are a worked example. The files are `tests/conftest.py`, `tests/test_tutor.py` and `tests/test_grader.py`.

**The block.** `tests/conftest.py` sets `models.ALLOW_MODEL_REQUESTS = False` at import time, with the comment "never hit a real LLM in tests". `test_tutor.py` sets it again at the top of the file.

**The tutor.** The `client` fixture in `test_tutor.py` starts the app and overrides the tutor agent: `get_tutor().override(model=TestModel(custom_output_text=REPLY))`. The tutor has no tools, so `TestModel` just returns that text. `REPLY` is a sample with one valid citation, one invalid citation and a code block. The tests then check what the **server** does with the text:

- it strips code blocks below hint level L4,
- it drops the citation that is not a section of the lesson,
- it sends the answer as server-sent events and saves it in the chat history,
- it sends live tokens only from L4.

One more test overrides the model with text that holds a `<script>` tag and a `javascript:` link, and checks that no script tag and no link come out as live HTML. The model is a constant, and the code around it is the thing under test. Plain rules such as `compute_ceiling`, `apply_ceiling` and `validate_citations` are tested with no agent at all.

**The grader.** `test_grader.py` builds a fresh agent with a helper called `fake_agent`. It makes `Agent(FunctionModel(respond), ..., output_type=NativeOutput(Grade), ...)`. The function `respond` appends to a list on every call, so the list counts the calls. It returns the n-th scripted verdict as JSON. The tests pass this agent into `grade_answer(...)` and check:

- three samples that agree give a settled result,
- one disagreeing sample makes a criterion `uncertain`,
- an answer that looks like an injection is flagged **without calling the model** (`calls == []`).

Another test uses the **real** grader agent from `make_grader()` with `override(model=FunctionModel(respond))`. The script records the first request and checks it, as in this lesson: the learner's answer sits in the user prompt between `<<<ANSWER>>>` markers and not in the instructions, and `info.model_request_parameters.output_mode` is `"native"`. The real grader is built from a named model, so that test sets a made-up key first. No request leaves the machine, because the override replaces the model.

**What these tests do not cover.** They cannot tell you whether a real model grades well. That is a different question. The repo keeps `evals/run_grader.py` for it. It uses real tokens, and the `evals` workflow runs only when someone starts it by hand.

Sources: [Unit Testing](https://pydantic.dev/docs/ai/guides/testing/), [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/), [Retries](https://pydantic.dev/docs/ai/core-concepts/retries/) and [Function Tools](https://pydantic.dev/docs/ai/tools-toolsets/tools/) from the Pydantic AI documentation, version 2.56.0, MIT licence, © Pydantic Services Inc. 2024 to present. This site is not affiliated with Pydantic.
