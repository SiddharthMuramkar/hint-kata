# Task: stop a runaway tool loop

This time the agent already exists. You add the guards that stop it when a model gets stuck.

Open `guard.py` in your workspace. It has a small research agent with two tools, and three TODO comments. Do not change the tools.

- `search(query)` always works and never finds a final answer. A model that keeps calling it is stuck in a loop.
- `fetch(url)` raises `ModelRetry` if the URL does not start with `https://`. For a host with `down.example` in it, it raises `ToolFailed`. So a model can loop on `fetch` too.
- `Deps` records every `search` and `fetch` call in two lists, so a test can count them.
- `Outcome` is the result of a guarded run: `finished`, `text` and `reason`.

Do these three things.

1. **Retry budget.** Give every tool a budget of 2 retries (the default is 1). It is one argument on the `Agent`. Read the lesson sections "Tool retries and output retries" and "The retry layers".
2. **Limits.** Make `LIMITS` stop a run after at most 5 model turns (`request_limit`) and at most 3 tool calls that succeed (`tool_calls_limit`). Read the section "Usage limits". The two limits catch different loops, so you need both.
3. **`run_guarded`.** Run the agent under `LIMITS`. If the run is stopped because a usage limit or a retry budget is used up, return `Outcome(finished=False, text="", reason=str(error))` and do not raise. If the agent answers, return `Outcome(finished=True, text=<the answer>, reason="")`. Catch only the two exceptions that mean "stopped": do not catch `Exception`, because a bug in your own tool should still show up.

## How the check works

The hidden tests need no API key and no network. They set `ALLOW_MODEL_REQUESTS = False` and swap the agent's model for a `FunctionModel` with `agent.override(...)`. The fake model plays these runs:

- It calls `search`, then answers. The run must finish.
- It calls `search` on every turn, for ever. The run must stop after exactly 3 searches, and the reason must name `tool_calls_limit`.
- It calls `fetch` on the down host on every turn, for ever. Those calls fail, so they are not counted as tool calls. The run must stop after exactly 5 fetches, and the reason must name `request_limit`.
- It calls `fetch` with two bad URLs and then a good one, then answers. The run must finish, so the budget must be 2.
- It calls `fetch` with a bad URL on every turn, for ever. The run must stop after 3 attempts, and the reason must say `max retries count of 2`.

The tests also check that your code does not catch `Exception`.

Press **Check my work** when you are ready. If a test fails, read its message and the lesson sections "Usage limits", "Tool retries and output retries" and "Reproducing a runaway loop in a test".

## Hints

- `UsageLimits(request_limit=..., tool_calls_limit=...)` takes both numbers as keyword arguments.
- A run takes limits as `agent.run_sync(prompt, deps=deps, usage_limits=LIMITS)`.
- The exceptions are `UsageLimitExceeded` (a limit was crossed) and `UnexpectedModelBehavior` (a retry budget was used up). The starter file already imports both.
- The retry budget argument takes a dict, like `{"tools": 2}`.
