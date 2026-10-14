# Task: write tests that catch a bug

This time you do not write the agent. You write the tests.

Your workspace has `support_agent.py`, a small support agent with two tools. Do not edit it.

- `lookup_order(order_id)` returns the amount paid for an order. For an unknown order it raises `ModelRetry` with a message that lists the known orders.
- `refund(order_id, amount)` refunds an order. It raises `ModelRetry` if the order was not looked up first, or if the amount is more than was paid.
- The dependencies are `SupportDeps`: the `orders` (id to amount paid), plus two lists the tools fill in: `looked_up` and `refunds`.
- The answer is a `SupportReply` with `order_id`, `refunded` and `message`.
- The model name is a real one (`openai:gpt-5.2`), so a test that forgets to swap the model must not reach it.

Open `test_support_agent.py`. It has six TODO comments. Turn each one into a test (or, for the first one, a line of setup).

1. Block real model requests for the whole file.
2. Run the agent with `TestModel` inside `capture_run_messages()`, and assert the order of the tool calls: `lookup_order` first, then `refund`.
3. Script a `FunctionModel` for the happy path: look up, refund, answer. Assert the output and `deps.refunds`.
4. Script a model that calls `refund` before `lookup_order`. Assert that the agent sent a retry prompt, and that the order was refunded only once.
5. Script a model that looks up an unknown order, then recovers. Assert the text of the retry prompt.
6. Assert `result.usage.requests` and `result.usage.tool_calls` for a run you scripted.

## How the check works

The checker runs your file twice, with no API key:

- against `support_agent.py`: every test must **pass**.
- against a hidden, broken copy of the agent: at least one test must **fail**. In the broken copy, `refund` can run before `lookup_order`, and nothing stops it.

A test that always passes is useless. If your tests also pass on the broken copy, they do not check the order of the work.

The checker also needs:

- At least 5 test functions in `test_support_agent.py`.
- `models.ALLOW_MODEL_REQUESTS = False` in your test file (or in a `conftest.py` next to it).

You can run your tests yourself:

```console
$ uv run pytest -q test_support_agent.py
```

## Hints

- `TestModel` makes up its arguments. Read the lesson section "Fast guesses with TestModel" to see which ones, then give `SupportDeps` an order with that id.
- To read the tool calls, look at the `ToolCallPart` objects inside the `ModelResponse` messages. Skip the call named `final_result`: it is the structured answer, not one of your tools.
- A scripted model that returns fixed replies in turn is easy to write with `iter(...)` and `next(...)`.
- A retry prompt is a `RetryPromptPart` inside a `ModelRequest`. Its `content` is the text your tool gave to `ModelRetry`.
- `SupportDeps` is a plain dataclass, so you can read `deps.refunds` after the run.
- `result.usage` is a property, not a method. Write it without parentheses.

If a test fails, read its message and the lesson sections "Reading the run with capture_run_messages", "Asserting tool order and arguments" and "Scripting retries".
