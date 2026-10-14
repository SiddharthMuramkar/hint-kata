---
id: pa6-instructions-and-settings
track: pydantic-ai
title: "Instructions and model settings"
minutes: 25
pins:
  pydantic-ai: "2.56.0"
sources:
  - pydantic-ai-core-concepts-agent
  - pydantic-ai-models-overview
  - pydantic-ai-guides-testing
---

Every request to a model carries two kinds of control. The first is words: the instructions that say who the model is and how to answer. The second is numbers: the settings that cap its length, set a timeout and say how hard it should think. In [PA1](/lessons/pa1-first-agent) you wrote one fixed instruction. Here the words follow your data, you learn where each setting can live and which one wins, and you see how this site's own tutor and grader are set up. At the end you check all of it without an API key.

A note on how to read this lesson. "I checked" means I ran a small script against Pydantic AI 2.56.0 with a fake model. A claim with a link is in the official docs. A few claims come only from the installed source code, and I say so each time.

## Instructions or a system prompt

Both are text the model reads before your question. The [Agents page](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions) recommends `instructions` for almost every case. It keeps `system_prompt` for one job: when you want the system prompts of earlier requests to stay in the history that is sent to the model.

The two travel differently. I checked with a `FunctionModel`, a fake model that is handed everything a real one would get:

```python
from pydantic_ai import Agent
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel


def spy(messages, info):
    print("instructions:", info.instructions)
    print("request parts:", [type(p).__name__ for p in messages[-1].parts])
    return ModelResponse(parts=[TextPart("ok")])


Agent(FunctionModel(spy), instructions="Be brief.").run_sync("hi")
# instructions: Be brief.
# request parts: ['UserPromptPart']

Agent(FunctionModel(spy), system_prompt="Be brief.").run_sync("hi")
# instructions: None
# request parts: ['SystemPromptPart', 'UserPromptPart']
```

Instructions are not a message part. The agent puts them beside the messages, on the request, and rebuilds them for every request. A system prompt is a `SystemPromptPart` inside the first request, so it becomes part of the conversation record.

That difference matters on a later run that passes `message_history`. [PA5](/lessons/pa5-message-history) explains history itself. Here is what each kind does with it.

- **Instructions** come from the agent you run now. Old requests keep a copy of the instructions they were sent with, but the docs say those copies are left out of the next request. I checked: agent A had "Be brief.", agent B had "Speak French.", and B ran on A's history. The model's `info.instructions` was only "Speak French."
- **A system prompt** stays in the history and is sent again with it. A new run adds its own system prompt only when the history is empty. I checked a history that held earlier turns but no system prompt, run by an agent with `system_prompt="SYS-NEW"`. The model never saw `SYS-NEW`. If your stored history lost its system prompt, it stays lost.

So ask where the text should live. If it belongs to the code you are running today, use `instructions`. If you want it frozen into one conversation's record, use `system_prompt`. Most of the time you want the first.

## Static, dynamic and per-run instructions

The Agents page lists three kinds of instructions, and one agent can use all three.

**Static** instructions are a string you give the constructor. They never change.

**Dynamic** instructions are functions registered with [`@agent.instructions`](https://pydantic.dev/docs/ai/core-concepts/agent/#instructions). They run each time the agent builds a request, not when the agent is built, so they can read the run's `deps`. A function may take `ctx: RunContext[Deps]` or no argument at all. It may be sync or async. It returns text, and an empty string adds nothing.

```python
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext


@dataclass
class Deps:
    tone: str
    max_words: int


agent = Agent(
    "openrouter:anthropic/claude-haiku-5.5",
    deps_type=Deps,
    instructions="You write replies for a support desk.",
    defer_model_check=True,  # lets the agent build before an API key exists
)


@agent.instructions
def persona(ctx: RunContext[Deps]) -> str:
    return f"Use a {ctx.deps.tone} tone. Keep replies under {ctx.deps.max_words} words."


async def load_rules(tone: str) -> str:  # stands in for a database or file read
    return f"House rules for a {tone} tone: no jargon."


@agent.instructions
async def house_rules(ctx: RunContext[Deps]) -> str:
    return await load_rules(ctx.deps.tone)
```

You can also give a function straight to the constructor, as in `Agent(..., instructions=my_function)`. This site's grader does that. The decorator is the same thing for a function you define after the agent.

Dynamic instructions run again on every run, even when you pass history. I checked with a counter in a sync and an async function. Run 1 used `Deps("formal", 50)`. Run 2 passed run 1's history and `Deps("casual", 50)`. Both counters reached 2, and the model's second request carried the casual text. A plain dynamic `@agent.system_prompt` function behaved the other way. Its counter stayed at 1, and the second request still held the old formal text. The docs point out this same contrast. A run that calls tools sends more than one request, and the function runs before each one. In my check, `ctx.run_step` was 1 and then 2.

**Runtime** instructions are given to one call: `agent.run_sync("...", instructions="Answer in one sentence.")`. They are extra text for that run only. I checked that the next run, without the argument, did not carry them. Use them for a one-off need that is not data in `deps`.

The parts are joined into one string with a blank line between them. The docs also say static text always sorts before dynamic text, so a provider that caches a prompt can keep the stable start and leave the changing end out. The docs class runtime instructions as dynamic. In 2.56.0 I found something different. I checked one static string, one function and one runtime string, and read `info.model_request_parameters.instruction_parts`. The runtime part was flagged static, and the order was static, then runtime, then the function. That is why the runtime text came before the function text. I then mapped those parts for OpenRouter with `openrouter_cache_instructions=True`. The cache marker landed on the runtime part, so a per-call runtime instruction sits inside the cached start and changes it on every call. Do not use `run(instructions=...)` for text that must stay outside the cache. Put it in an `@agent.instructions` function instead. The [Instruction parts](https://pydantic.dev/docs/ai/core-concepts/agent/#instruction-parts) section shows how to inspect each part and give it a name.

## Model settings

Instructions are words. [`ModelSettings`](https://pydantic.dev/docs/ai/core-concepts/agent/#model-run-settings) is the numbers. It is a `TypedDict` with every key optional, so `ModelSettings(max_tokens=300)` is just the dict `{'max_tokens': 300}`. It holds the options that many providers share, such as `max_tokens`, `timeout`, `temperature` and `top_k`. A model uses the keys it understands.

Two keys matter most here.

- `max_tokens` caps the length of one reply. Set it on every agent. It is the cheapest cost guard you have.
- `timeout` is how many seconds to wait for one request.

Two more keys are shared across providers. They are in the installed source, in the docstrings of `ModelSettings`, and not on the Agents page.

- `thinking` is `True`, `False` or an effort: `'minimal'`, `'low'`, `'medium'`, `'high'` or `'xhigh'`. It is one name for "how hard should the model reason", translated for each provider.
- `cache` is `True`, `False`, a lifetime such as `'5m'` or `'1h'`, or a small dict. It asks the provider to cache the stable start of the prompt, which is the tool definitions and the static instructions, and optionally the conversation too. Writing to a cache costs a little more than plain input, and reading from it costs much less. It pays off when the same start is sent again and again.

A model class translates these two keys only when its profile says it can. I checked a plain `FunctionModel`: it dropped both without a word. A `FunctionModel` whose profile claimed support passed `thinking` and `cache` on in `info.model_request_parameters.thinking` and `.cache`, and neither stayed in `info.model_settings`. Through `OpenRouterModel("anthropic/claude-haiku-5.5")`, `thinking="low"` became `openrouter_reasoning={'effort': 'low', 'enabled': True}`, and `cache=True` became `openrouter_cache_*` settings with a five-minute lifetime. A later section shows the provider side of that.

Thinking uses tokens, and they count against `max_tokens`. If the cap runs out while the model is still thinking, there is no answer to return. The Models Overview page [mentions this case](https://pydantic.dev/docs/ai/models/overview/#finish-reason-example). I checked with a fake reply that held only a thinking part and a `length` finish reason. The run raised `UnexpectedModelBehavior` and told me to raise `max_tokens`. Leave room for thinking.

One more tool, mentioned once. `max_tokens` caps one reply. [`UsageLimits`](https://pydantic.dev/docs/ai/core-concepts/agent/#usage-limits) caps a whole run, in tokens, requests, tool calls or cost, and you pass it as `usage_limits=` to a run. PA11 covers it.

## Which setting wins

Settings can be set in three places, and the [docs](https://pydantic.dev/docs/ai/core-concepts/agent/#model-run-settings) give the order. The model comes first, then the agent, then the run. A later place wins.

1. **Model.** `settings=` on a model instance. These are the base defaults for that model.
2. **Agent.** `model_settings=` on `Agent(...)`.
3. **Run.** `model_settings=` on `run`, `run_sync` or `run_stream`.

Mind the names. It is `settings=` on a model and `model_settings=` on an agent and a run. The docs add a layer for capabilities, such as `Thinking()`, between the agent and the run.

The places merge key by key. A run that names one key does not erase the others. I checked with a fake model that records what it receives:

```python
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel

seen = []


def record(messages, info):
    seen.append(info.model_settings)
    return ModelResponse(parts=[TextPart("ok")])


model = FunctionModel(record, settings=ModelSettings(max_tokens=500, timeout=30))  # 1. model
agent = Agent(model, model_settings=ModelSettings(max_tokens=300))  # 2. agent
agent.run_sync("hi", model_settings=ModelSettings(max_tokens=100))  # 3. run
print(seen[-1])
# {'max_tokens': 100, 'timeout': 30}
```

`max_tokens` came from the run and `timeout` came from the model. The agent's 300 lost to the run. In `info.model_settings` the model sees the merged result.

Two details. First, the merge is shallow. A key that holds a dict is replaced as a whole. I checked with an agent whose `openrouter_reasoning` was `{'effort': 'low', 'exclude': True}` and a run whose value was `{'effort': 'high'}`. The model got `{'effort': 'high'}` and `exclude` was gone. Second, to clear a key that an earlier place set, give it `None`. The docs show this, and I checked it with `timeout=None`.

Sometimes the value depends on the run. Both agent-level and run-level `model_settings` can also be [a function that takes a `RunContext`](https://pydantic.dev/docs/ai/core-concepts/agent/#dynamic-model-settings), called before each request. A simple rule works for most code. Put values that never change on the agent. Put a value that changes from call to call on the run. The task does this with the token cap.

## Provider settings and the temperature rule

Each provider has settings that the shared keys cannot express. For these, Pydantic AI has a subclass of `ModelSettings` per provider, such as `GoogleModelSettings` on the Agents page's [Model specific settings](https://pydantic.dev/docs/ai/core-concepts/agent/#model-specific-settings) section. For OpenRouter it is `OpenRouterModelSettings`. Its keys all start with `openrouter_`, and they mix freely with shared keys like `max_tokens`. The page for the provider is [OpenRouter](https://pydantic.dev/docs/ai/models/openrouter/). What follows comes from the installed source.

```python
from pydantic_ai.models.openrouter import OpenRouterModelSettings

settings = OpenRouterModelSettings(
    openrouter_reasoning={"effort": "low"},
    openrouter_cache_instructions=True,
    max_tokens=1200,
)
```

- `openrouter_reasoning` controls reasoning. `effort` takes `'minimal'`, `'low'`, `'medium'`, `'high'`, `'xhigh'` or `'none'`. This repo's rule file says never to use `'none'` on Sonnet 5.5.
- `openrouter_cache_instructions` asks OpenRouter to mark the instructions for caching. `True` means a five-minute lifetime, and `'1h'` is allowed. It works for Anthropic and Gemini models behind OpenRouter.
- `openrouter_provider` holds routing preferences, such as `require_parameters` and the zero-data-retention switch `zdr`.

Provider keys beat the shared ones. I checked that when `openrouter_reasoning` is set, `thinking` is ignored, and that when any `openrouter_cache_*` key is set, the shared `cache` adds nothing.

A closer look at `openrouter_cache_instructions`. Caching works on a stable start, so the marker goes after the last part that is not flagged dynamic. I mapped requests by hand. With one static part and one dynamic part, the marker sat on the static part and the dynamic text came after it, unmarked. With only dynamic instructions, no marker was placed at all. With a runtime part in the middle, the marker sat on the runtime part, as the previous section showed. Keep that in mind when you split your text between static, runtime and dynamic.

Now the rule this site follows: **never set `temperature` or `top_p` on Claude 5.x models, and set `max_tokens` instead.** It is in this repo's `.claude/rules/agents.md`. Pydantic AI knows these models do not take sampling settings: for `anthropic/claude-haiku-5.5` on OpenRouter, the profile flag `anthropic_disallows_sampling_settings` is `True`. I checked what happens on the OpenRouter path, though. `prepare_request` with `{'temperature': 0.2, 'max_tokens': 100}` returned both keys and printed no warning. The source says the Anthropic adapter drops such keys with a warning, but I did not run it, because the `anthropic` package is not installed in this project. So on this path nothing protects you, and the rule has to be a habit. It also means temperature 0 cannot make a grader repeatable. This site's grader takes three samples instead, and marks a criterion as uncertain when they disagree.

Here is how the two agents in `app/agents/` follow the rules. I captured the request each one builds, with a fake network.

- **The tutor** (`tutor.py`) has agent-level `OpenRouterModelSettings` with `max_tokens=1200`, `openrouter_reasoning={"effort": "low"}`, `openrouter_cache_instructions=True` and `openrouter_provider`. That last one is `{"zdr": True, "data_collection": "deny"}` when the owner turns on zero-data-retention routing, and an empty dict otherwise. It has no temperature. All its instructions come from one dynamic function, `_instructions(ctx: RunContext[TutorDeps])`, which builds the text from the lesson sections, the hint ladder, the ceiling and the learner's attempts.
- **The grader** (`grader.py`) uses `NativeOutput(Grade)`, and passes a dynamic `_instructions` function to the constructor that builds the rubric text from its deps. Its settings are `max_tokens=1500`, `openrouter_reasoning={"effort": "low"}` and `openrouter_provider` with `require_parameters: True`, plus the zero-data-retention keys when that switch is on. No temperature, and no cache setting.

One thing I noticed while checking. Since the tutor's instructions are all dynamic, its request had a plain system message and no cache marker, so `openrouter_cache_instructions=True` currently has nothing to mark in 2.56.0. Moving the unchanging text, the ladder and the rules, into a static `instructions=` string would give it something. This lesson does not change the tutor. It is a note for later.

## Testing what the model saw

Instructions and settings are easy to get wrong silently, and a test can read them. A `FunctionModel` function receives an `AgentInfo`. Three of its fields matter here: `info.instructions` is the text the agent built for this request, `info.model_settings` is the merged settings, and `info.model_request_parameters` holds the resolved `thinking` and `cache` and the individual instruction parts, each with a `dynamic` flag. The [Unit Testing page](https://pydantic.dev/docs/ai/guides/testing/) describes `FunctionModel`, `TestModel`, `Agent.override` and `ALLOW_MODEL_REQUESTS`.

```python
from pydantic_ai import models

models.ALLOW_MODEL_REQUESTS = False  # a real model call would raise

seen = []


def record(messages, info):
    seen.append(info)
    return ModelResponse(parts=[TextPart("ok")])


with agent.override(model=FunctionModel(record)):
    agent.run_sync("hi", deps=Deps("brief", 40), model_settings=ModelSettings(max_tokens=150))

assert "brief" in (seen[0].instructions or "")
assert seen[0].model_settings["max_tokens"] == 150
```

The test never reads the agent's own fields. It reads what the model received, which is what matters. A test like this fails if someone moves a setting to the wrong layer, forgets to make a function dynamic, or sets a key that gets dropped.

That is the whole kit for the task. You build a persona agent whose instructions come from `deps`, with a token cap that follows its tone. The hidden tests play the model, so no key or network is needed.

Sources: [Agents](https://pydantic.dev/docs/ai/core-concepts/agent/), [Models Overview](https://pydantic.dev/docs/ai/models/overview/) and [Unit Testing](https://pydantic.dev/docs/ai/guides/testing/) from the Pydantic AI documentation, version 2.56.0, MIT licence. © Pydantic Services Inc. 2024 to present. The remarks on the shared `thinking` and `cache` keys, the OpenRouter settings, where the cache marker goes (including on runtime instructions) and how temperature is handled come from the installed 2.56.0 source code and my own checks, not from these pages. This site is not affiliated with Pydantic.
