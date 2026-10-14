# Task: build your first agent

Edit `first_agent.py` in your workspace. It has two TODOs.

## What to build

1. **`CityFacts`** is a Pydantic model with exactly three fields:
   - `city` (`str`)
   - `country` (`str`)
   - `population` (`int`)
2. **`make_agent()`** returns a Pydantic AI `Agent` that:
   - reads its model string from the environment variable `TUTOR_MODEL`. If the variable is missing or empty, it falls back to `DEFAULT_MODEL`.
   - has `instructions` (not `system_prompt`). The instructions must contain the word **concise**.
   - has `output_type=CityFacts`, so it returns a `CityFacts` object instead of text.

Use what you learned: the model string is `provider:model`, instructions go in `instructions=`, and the structured answer comes from `output_type=`.

## How to check

Press **Check my work** in the lesson page. The hidden tests use a `TestModel`, so no API key or network is needed. They check that:

- `CityFacts` has the three fields.
- `make_agent()` returns an `Agent` whose `output_type` is `CityFacts` and whose model comes from `TUTOR_MODEL`.
- running the agent gives back a `CityFacts` instance.
- the instructions mention "concise".

Want to see it work for real? Set `OPENROUTER_API_KEY` and run `python first_agent.py` from your workspace folder. That makes one small paid call.
