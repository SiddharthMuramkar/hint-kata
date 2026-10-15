---
id: pa11-production-basics
track: pydantic-ai
title: "Production basics: Logfire, retries, usage limits"
minutes: 40
pins:
  pydantic-ai: "2.56.0"
  logfire: "5.2.0"
sources:
  - pydantic-ai-integrations-logfire
  - pydantic-ai-core-concepts-retries
  - pydantic-ai-core-concepts-agent
  - pydantic-ai-project-version-policy
---

An agent in a demo runs once while you watch. An agent in production runs when nobody is watching, and a model can get stuck: it calls the same tool again and again, and each turn costs money. Three habits keep that safe. Cap what a run may do. Know which retries you have turned on and what they add up to. Record every run so you can read it afterwards. In this lesson you learn the retry layers of Pydantic AI, the budgets for tool and output retries, `UsageLimits`, how to reproduce a runaway loop in a test with `FunctionModel`, what Logfire and OpenTelemetry record, and what the version policy lets change under you. We ran the examples on Pydantic AI 2.56.0 and Logfire 5.2.0. A point that comes only from the docs is marked as such.

## Why a run needs a guard

A run of an agent is a loop. The model answers with a tool call, the agent runs the tool and sends back the result, the model answers again, and so on until it gives a final answer. Nothing in that loop forces the model to stop. A tool that always returns "no results yet" can keep a model asking for a long time.

We built exactly that: a fake model that calls one tool on every turn, and a tool that always works. With no limits set, we saw the run stop by itself after 50 model requests, and the tool had run 50 times. The error was `UsageLimitExceeded`. So Pydantic AI already has a safety net: the [Retries](https://pydantic.dev/docs/ai/core-concepts/retries/#retry-multiplication) page says the default `request_limit` is `50`. Fifty real requests can still cost a lot, and 50 turns is a long wait for a user. So you set your own, smaller limits.

The rest of the lesson has two halves. First the guards: retries and limits. Then the recording: Logfire.

## The retry layers

The word "retry" means different things at different layers of a run. The [Retries](https://pydantic.dev/docs/ai/core-concepts/retries/#the-layers) page lists seven, and says they do not share a budget:

1. **Transport.** The same HTTP request is sent again by a retrying transport on your HTTP client. Nothing retries here unless you install one.
2. **Provider SDK.** The same request is sent again by the provider's own client library.
3. **Durable execution.** A workflow engine runs the whole model request again.
4. **Model fallback.** The same request goes to a different model. It is not a retry of the same model.
5. **Tool retry.** The model is asked to fix one tool call.
6. **Output retry.** The model is asked to fix its final answer.
7. **Model-request hooks.** A hook raises `ModelRetry` and a new request is sent.

The first four are invisible to the model. It never learns that an attempt failed. The last three are the agent retries. Each one is another model request, so it costs a turn, and each one puts a `RetryPromptPart` into the message history. You saw that part in the testing lesson.

This split matters for the rest of the lesson. The limits below count the turns of the agent loop. They do not see the layers underneath.

## Tool retries and output retries

A tool retry is a note to the model: the call did not work, here is why, try again. It happens when the arguments fail validation, when the tool raises `ModelRetry`, when a tool times out, or when the model calls a tool that does not exist. The [Retries](https://pydantic.dev/docs/ai/core-concepts/retries/#tool-retries) page gives three rules about the counter:

- It is kept per tool name, and it is cleared when that tool succeeds. There is no budget for the whole run. A tool that fails, then succeeds, then fails again never runs out of a budget of one.
- `max_retries=N` means N retries, so N+1 attempts.
- A tool name the model made up gets its own fresh budget.

When a tool has used up its budget, the run raises `UnexpectedModelBehavior`. The default budget is one retry.

You set the budgets with one argument, `retries`. A plain number sets both the tool and the output budget. A dict sets only the keys you name. A tool can also have its own number.

```python
from pydantic_ai import Agent, ModelRetry

agent = Agent(
    "openai:gpt-5.2",
    retries={"tools": 3, "output": 1},  # keys you leave out keep the default of 1
    defer_model_check=True,
)


@agent.tool_plain(retries=5)  # this tool may ask for 5 retries, whatever the agent says
def find_user(name: str) -> int:
    if " " not in name:
        raise ModelRetry("Give the full name.")
    return 123
```

We checked the counting with a fake model that always calls a tool that always raises `ModelRetry`. With the default budget the tool ran 2 times and then the run raised `UnexpectedModelBehavior` with the text `exceeded max retries count of 1`. With `retries={"tools": 3}` it ran 4 times. With a tool that raised `ModelRetry` on every odd call and worked on every even call, the budget was never used up, and only a request limit ended the run.

The output budget is separate. It covers an answer that fails validation or that an output validator rejects. The [Retries](https://pydantic.dev/docs/ai/core-concepts/retries/#output-retries) page says how it is counted depends on how the model returns its answer. We did not run this part.

There is also a deliberate opposite of `ModelRetry`: `ToolFailed`. The docs say it records a tool return marked as failed and does not use up the retry budget. So failures that raise `ToolFailed` are bounded by usage limits, not by a retry count. We ran it. A loop on a tool that always raised `ToolFailed("down")` was never stopped by a retry budget. The history held five tool returns, all with `outcome='failed'`, until the request limit ended the run.

Some things are never retried. An exception from a tool that is not `ModelRetry` or `ToolFailed` goes out of the run, as it should. A bug in your tool should show up, not be hidden. The docs also say that nothing re-runs a whole agent for you.

## Retries multiply

The layers do not share a budget, but they stack. The [Retries](https://pydantic.dev/docs/ai/core-concepts/retries/#retry-multiplication) page works it out. Let N be the model requests of one run, F the models a fallback can try, M the attempts of the provider SDK client and K the attempts of the transport. In the worst case one run puts `N × F × M × K` requests on the network.

Here is our own example. A run that takes 4 turns, with a fallback of 2 models, an SDK that allows 3 attempts, and a transport that allows 2 attempts, can send up to 4 × 2 × 3 × 2 = 48 requests in the worst case. Every one of them has its own wait, and a request that reaches the model is billed.

Now read the limits with that in mind. The docs say `UsageLimits` bounds only N. The request count is the number of model responses the agent acts on, one per turn. It does not count the attempts that a fallback model moved on from, and it does not count SDK or transport retries. Their tokens and cost do count towards the token and cost limits when the provider reports them. So a request limit of 4 does not mean four requests on the wire. Size your budgets for the worst case, not for the happy path.

## Usage limits

`UsageLimits` is a small object that you pass to a run as `usage_limits=...`. The [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/#usage-limits) page lists what it can cap:

- `request_limit`: the number of model turns. This is the one that stops infinite loops.
- `tool_calls_limit`: the number of tool calls that ran successfully.
- Token limits, for example `output_tokens_limit`. They are checked after a response comes back, so the response that crosses the line has already been paid for. `per_request_input_tokens_limit` caps the size of one request instead of the whole run.
- `cost_limit`: a ceiling in US dollars.

When a limit is crossed, the run raises `UsageLimitExceeded`. We ran the first two with a fake model that loops.

```python
from pydantic_ai import Agent, UsageLimitExceeded, UsageLimits, models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False


def loop_forever(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart("search", {"query": "again"})])


agent = Agent(FunctionModel(loop_forever))
queries: list[str] = []


@agent.tool_plain
def search(query: str) -> str:
    queries.append(query)
    return "No answer yet."


try:
    agent.run_sync("Find it", usage_limits=UsageLimits(request_limit=3))
except UsageLimitExceeded as exc:
    print(exc)  # The next request would exceed the request_limit of 3. ...
print(len(queries))  # 3
```

The tool ran 3 times and the fourth request was refused before it was sent. The error says `The next request would exceed the request_limit of 3`. With `UsageLimits(tool_calls_limit=2)` instead, the tool ran 2 times and the error said `The next tool call(s) would exceed the tool_calls_limit of 2 (tool_calls=3)`.

The docs say one more thing about `tool_calls_limit`: it is checked before the tools run. If the model asks for three tools in one reply and the limit is two, none of them run. We saw this: with a limit of 2 and three calls in one reply, the tool ran 0 times.

The two limits catch different loops. We ran a loop on a tool that raised `ToolFailed` on every call. It never used the tool call count, because no call succeeded, and it never used a retry budget. Only `request_limit` stopped it, after 5 turns for a limit of 5. A loop on a tool that always works is caught by either limit. So set both: `tool_calls_limit` for runs that do too much work, and `request_limit` as the backstop for every kind of loop.

About `cost_limit`. The docs say cost is a best effort. For a model with no price data the cost is empty, and they say not to treat the limit as a hard billing guarantee. They tell you to pair it with `request_limit` or with spending controls from your provider. We saw why: with a fake model, which has no price, `cost_limit` never fired, and `request_limit` ended the run.

One more habit. Catch `UsageLimitExceeded` at the edge of your app and turn it into a plain answer for the user, such as "I could not finish this. Please try a narrower question." Also log it. A stopped run is a signal that something is wrong, either with the tools or with the prompt.

## Reproducing a runaway loop in a test

A guard you have never seen fire is a guess. The testing lesson gave you the tool for this: `FunctionModel` plays the model, so you can make it misbehave. The example above is already a test in disguise. Here is the shape of a good one, using what you know from the earlier lesson:

```python
import pytest
from pydantic_ai import Agent, UsageLimitExceeded, UsageLimits, models
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

models.ALLOW_MODEL_REQUESTS = False

agent = Agent("openai:gpt-5.2", defer_model_check=True)
calls: list[str] = []


@agent.tool_plain
def search(query: str) -> str:
    calls.append(query)
    return "No answer yet."


def loop_forever(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart("search", {"query": "again"})])


def test_a_search_loop_is_stopped() -> None:
    with agent.override(model=FunctionModel(loop_forever)):
        with pytest.raises(UsageLimitExceeded, match="tool_calls_limit of 3"):
            agent.run_sync("Find it", usage_limits=UsageLimits(tool_calls_limit=3, request_limit=5))
    assert len(calls) == 3  # the tool did the work 3 times and no more
```

Assert two things: the right error, and how far the loop got. The count of tool calls is the proof that the guard works. If you loosen the limit by mistake, the count changes and the test fails.

This site has a test file for the claims in this lesson, `tests/test_lesson_pa11_claims.py`. It runs each loop above and checks the counts. If an upgrade of Pydantic AI changes one of them, that test fails, and the lesson needs a second look. You can do the same for the guards of your own agents. The task for this lesson asks you to add the guards to an agent and shows a hidden test with loops like these.

## Logfire and OpenTelemetry

Limits stop a bad run. They do not tell you why it happened. For that you need a record. [Pydantic Logfire](https://pydantic.dev/docs/ai/integrations/logfire/) is a hosted observability product from the team behind Pydantic. The docs call it a commercial product with a free tier, so check the pricing page for the current limits. It is built on OpenTelemetry (OTel), an open standard for traces.

The support in Pydantic AI is built in and optional. The docs say that when the `logfire` package is installed and configured and you turn instrumentation on, details of each run are sent. Otherwise there is almost no cost and nothing is sent. The Logfire SDK comes with `pydantic-ai`, and with the slim package it is the `logfire` extra. This project pins `logfire[fastapi]==5.2.0`.

Turning it on takes two lines. You also need to log in once and pick a project, with `uv run logfire auth` and `uv run logfire projects new`. The docs show the setup, and the CLI writes a `.logfire` folder that the SDK reads.

```python
import logfire
from pydantic_ai import Agent

logfire.configure()  # find the project and its write token
logfire.instrument_pydantic_ai()  # trace every agent run in this process

agent = Agent("openai:gpt-5.2", name="hello_world_agent", instructions="Reply in one sentence.")
result = agent.run_sync("Where does the phrase hello world come from?")
print(result.output)
```

Two details. The `name` is optional but useful: it labels the run in Logfire. Without it Pydantic AI guesses the name from the variable and falls back to `agent`, which is no help when several agents run in one app. And `logfire.configure()` can take the token directly. This site passes it from the `LOGFIRE_TOKEN` setting with `send_to_logfire="if-token-present"`, so with no token it sends nothing and the tests run without an account.

A fact about this site, so you do not assume more than is there: `app/main.py` configures Logfire and calls `logfire.instrument_fastapi(app)` when a token is set. It sends the app's own logs too. It does not call `instrument_pydantic_ai`, so the tutor and grader runs are not traced yet.

Until you configure instrumentation, the docs say the first agent run in a process prints a short banner to the error stream. It is not shown under `pytest` or when the `CI` variable is set. We saw it when we ran a plain script. Set `PYDANTIC_AI_NO_BANNER` to turn it off.

Because Logfire speaks OpenTelemetry, you can send the same data somewhere else. The docs show `logfire.configure(send_to_logfire=False)` with the `OTEL_EXPORTER_OTLP_ENDPOINT` variable pointing at your own collector, and also plain OTel without Logfire. Pydantic AI follows the OpenTelemetry conventions for generative AI, version 1.37.0 of them, so any backend that understands them can show the runs.

## What one run looks like in a trace

The docs say a trace is made for each run, with a span for every model request and every tool call. We checked the shape. We ran a looping agent named `looper` with `request_limit=2`, and read the spans from an in-memory exporter. The same spans are what Logfire shows. Plain OpenTelemetry was enough:

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic_ai import Agent
from pydantic_ai.capabilities import Instrumentation
from pydantic_ai.models.instrumented import InstrumentationSettings

exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))
settings = InstrumentationSettings(tracer_provider=provider)

agent = Agent(
    "openai:gpt-5.2",
    name="looper",
    capabilities=[Instrumentation(settings=settings)],
    defer_model_check=True,
)
# run it with a fake model, then: [span.name for span in exporter.get_finished_spans()]
```

For the stopped run the span names were, in the order they finished:

1. `chat` and the model name (the first model request),
2. `execute_tool search`,
3. `chat` and the model name again (the second request),
4. `execute_tool search`,
5. `invoke_agent looper`, the run itself, with the status `ERROR` because the limit stopped it.

The model name in the `chat` span is the name of our fake model; with a real model it is that model's name. The run span ends last, so it is last in the list. The model and tool spans hang under the run span. The run span carries the summed token use in `gen_ai.aggregated_usage.*` attributes, and each model request carries its own `gen_ai.usage.*`. The docs say this split is on purpose, so a backend that adds up usage across parent and child spans does not count twice.

What do you look for here? A run with many `chat` and `execute_tool` pairs and no answer is a loop. A run that ends in `ERROR` with a limit message is a guard that fired. Spans that repeat the same tool with the same arguments show the model going in circles. The docs also list metrics, such as token use and estimated cost per request, and prompt-cache health attributes on the model spans. We did not run those.

## Keeping private data out of traces

A trace records what was said. By default that includes the user's prompt, the tool arguments and results, and the model's reply. In a real app those can hold names, emails or customer text. The docs give a switch: `include_content=False` leaves the content out and keeps the structure.

```python
from pydantic_ai import Agent
from pydantic_ai.capabilities import Instrumentation
from pydantic_ai.models.instrumented import InstrumentationSettings

settings = InstrumentationSettings(include_content=False)
agent = Agent(
    "openai:gpt-5.2", capabilities=[Instrumentation(settings=settings)], defer_model_check=True
)
# or, for every agent in the process:
Agent.instrument_all(settings)
```

We ran it with a prompt `my-private-prompt` and a tool argument `my-question`. Neither string appeared in any attribute of any span, and the `tool.call.arguments` attribute was gone from the tool spans. The spans, the timing and the token counts stayed. That is usually enough to debug a loop. The docs also say that, with this setting, an exception recorded on a span keeps only its type, because the message could quote the content.

There is a related surprise. In another run we put the word `secret` in a tool argument and the Logfire SDK replaced the value with a `Scrubbed due to 'secret'` marker. That comes from the Logfire SDK, not from the page we used, so we cannot say how much it covers. Do not rely on it to protect private data. Use `include_content=False`.

## What can change under you

An app that depends on a library for years needs to know what the library promises. The [Version Policy](https://pydantic.dev/docs/ai/project/version-policy/) page says:

- V2.0 was released on June 23, 2026. Breaking changes are not made on purpose in minor releases. Something marked deprecated is not removed until the next major version, which will not come sooner than 3 months after V2.0. V1 gets security fixes for at least 6 months after V2.
- Some changes are **not** counted as breaking and can arrive in a minor release. Four matter here. A bug fix that breaks code which relied on something undocumented. New message parts, new stream events or new optional fields. A change to the OpenTelemetry span attributes, because backends support different versions of the conventions, so the default instrumentation version can change in a minor release. And a change to `__repr__`.
- A `beta` module holds features still in progress. Their API can change in a way that breaks your code.

What does that mean for the work in this lesson? The names of exceptions such as `UsageLimitExceeded` and the arguments of `UsageLimits` are documented API, so they are stable. The span attributes are not. If you build an alert on `gen_ai.aggregated_usage.input_tokens`, you can lose it in a minor release. The same goes for the exact text of an error message: the tests of this site match on short pieces such as `request_limit of 3`, and that is a reason to keep a test like the claims file. Pin the version, as this project does with `pydantic-ai-slim[openrouter]==2.56.0`, read the release notes when you upgrade, and test the behaviours you depend on.

The docs also say that a permitted change that needs your code to change comes with a "compatibility impact" note in its release notes. So the release notes are where you look first.

## Try it yourself

The task gives you `guard.py`, a small research agent with two tools. `search` always works and never finds an answer. `fetch` asks for a retry on a bad URL and fails with `ToolFailed` for one host that is always down. You add three things: a retry budget of 2 for the tools, run limits of 5 turns and 3 tool calls, and a function that returns an `Outcome` when a run is stopped instead of raising. The hidden tests use `FunctionModel` loops like the ones in this lesson. Open `task/README.md` for the steps.

Sources: [Pydantic Logfire Debugging and Monitoring](https://pydantic.dev/docs/ai/integrations/logfire/), [Retries](https://pydantic.dev/docs/ai/core-concepts/retries/), [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/) and [Version Policy](https://pydantic.dev/docs/ai/project/version-policy/) from the Pydantic AI documentation, version 2.56.0, MIT licence, © Pydantic Services Inc. 2024 to present. This site is not affiliated with Pydantic or Logfire.
