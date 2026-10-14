# Task: a triage agent that rejects bad tickets

You will build a small support triage agent. It reads a message and returns a `Ticket`. Pydantic checks that the answer has the right shape, but only your code knows the helpdesk rules: a priority is from 1 to 5, and a summary fits in 120 characters. You enforce those rules with an output validator that asks the model to try again.

Open `triage.py` in your workspace. It has two TODO comments.

1. **`Ticket`** is a Pydantic model with three plain fields:
   - `category`: one of `"bug"`, `"billing"` or `"other"` (use `Literal`)
   - `priority`: an `int`
   - `summary`: a `str`

   Do not add `Field(ge=..., le=...)` or `max_length`. Pydantic's own checks would then reject the answer before your validator runs. In this task the rules belong in the validator.
2. **`make_agent()`** already builds an `Agent` with `output_type=Ticket`. Register a function with `@agent.output_validator` that receives the ticket and returns it. Before returning, it must:
   - raise `ModelRetry` if the priority is not a whole number from 1 to 5. The message must mention the priority and the numbers 1 and 5.
   - raise `ModelRetry` if the summary is longer than 120 characters. The message must contain `120`.

Write messages the model can act on. "Invalid" does not tell it what to change.

## How the check works

The hidden tests use a `FunctionModel` as a scripted fake model and set `ALLOW_MODEL_REQUESTS = False`, so no API key is needed. They also set `TUTOR_MODEL=test`, so `make_agent()` builds without a key. Do not run the agent on that built-in `test` model yourself: it invents values such as a priority of 0, which your own validator rejects, so the run fails. That is why the tests script a `FunctionModel`. The fake model first returns an invalid ticket through the output tool, then a valid one. The tests check that:

- `Ticket` has the three fields, and `category` rejects values outside the list.
- a valid ticket needs no retry, and the boundary values (priority 1 and 5, a summary of exactly 120 characters) are accepted.
- a priority of 0, 6, 9 or -1 gives exactly one retry prompt, written by your `ModelRetry`, and the second answer becomes the output.
- a summary of 121 characters gives one retry prompt that contains `120`.
- the retry prompt is part of the second request sent to the model.

Press **Check my work** when you are ready. If a test fails, read its message and the lesson section "Output validators and ModelRetry".

Want to see it work for real? Set `OPENROUTER_API_KEY` and run `uv run python triage.py` from your workspace folder. That makes one small paid call.
