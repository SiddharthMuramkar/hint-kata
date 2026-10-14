# Task: a persona agent whose instructions and token cap follow its deps

You will build a small support-desk agent. The caller decides the **tone** of the reply and the **most words** it may have. Those two values travel in a `deps` object, so the instructions must be built from them on every run. The token cap also depends on the tone, so you set it for one run at a time.

Open `persona.py` in your workspace. `make_agent()` already builds the agent with a static instruction and an agent-level default (`max_tokens=1000`, `timeout=20`). It has four TODO comments.

1. **`PersonaDeps`** is a dataclass. Add two fields: `tone: str` and `max_words: int`.
2. **`settings_for(tone)`** returns `ModelSettings(max_tokens=...)`. Read the number from `TONE_TOKENS`: `brief` is 150, `friendly` is 300 and `formal` is 450. Any other tone gets `DEFAULT_TOKENS` (300). Set nothing else in it. This site never sets `temperature` or `top_p` on Claude 5.x models.
3. **A dynamic instructions function.** Inside `make_agent()`, register a function with `@agent.instructions`. It takes `ctx: RunContext[PersonaDeps]` and returns text that names the tone and the word limit from `ctx.deps`, for example `Use a brief tone. Keep every reply under 40 words.` Keep the static `instructions=STATIC` as it is.
4. **`ask(...)`** runs the agent once. Call `agent.run_sync` with the prompt, `deps=deps`, `message_history=history` and `model_settings=settings_for(deps.tone)`, and return the result.

Think about why step 4 uses a run-level `model_settings` and not the agent-level one. The tone changes from call to call, and the agent is built once.

## How the check works

The hidden tests use a `FunctionModel` as a recording fake model, and set `ALLOW_MODEL_REQUESTS = False`, so no API key or network is needed. The fake model keeps the `AgentInfo` of each request, so the tests can read exactly what the model was sent. They check that:

- `PersonaDeps` is a dataclass with the fields `tone` and `max_words`, in that order.
- the instructions the model saw start with the static text and then name the tone and the word limit from the deps.
- after a second run with the first run's history and new deps, the model sees the new tone and limit and nothing from the old deps.
- `settings_for` gives 150, 300 and 450 for the three tones, 300 for any other tone, and contains only `max_tokens`.
- the model request carries the tone's `max_tokens` (the run-level value beat the agent's 1000) and still carries the agent's `timeout` of 20, because settings the run does not name are kept.
- three runs with different tones each get the cap for their own tone.

Press **Check my work** when you are ready. If a test fails, read its message and the lesson sections "Static, dynamic and per-run instructions" and "Which setting wins".

Want to see it work for real? Set `OPENROUTER_API_KEY` and run `uv run python persona.py` from your workspace folder. That makes two small paid calls.
