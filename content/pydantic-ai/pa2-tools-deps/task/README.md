# Task: a price tool with dependencies

You will build a small shop agent. It has one tool, `price_of`, that reads a price catalogue from the agent's dependencies. When the model asks for an item that is not in the catalogue, the tool asks the model to try again.

Open `tools_task.py` in your workspace. It has three TODO comments.

1. **`Deps`**: make it a dataclass with one field, `prices: dict[str, float]`.
2. **`make_agent`**: tell the agent its dependency type with `deps_type=Deps`.
3. **`price_of`**: register a tool with the right decorator, so that the first parameter is `ctx: RunContext[Deps]` and the second is `item: str`.
   - Give it a docstring. The model reads it.
   - Return `ctx.deps.prices[item]`.
   - If the item is not in the catalogue, raise `ModelRetry("Unknown item, try one of: ...")` and list the known items after the colon, for example `Unknown item, try one of: coffee, tea`.

Do not read the catalogue from a global variable. The tests pass different `Deps` objects and expect the tool to use them.

## How the check works

The hidden tests use a `FunctionModel` as a scripted fake model, and set `ALLOW_MODEL_REQUESTS = False`, so no API key is needed. The fake model first asks for a misspelled item, reads the retry prompt your tool produced, then asks for a valid item and answers with the price. The tests check that:

- `make_agent().deps_type` is your `Deps` class and the agent advertises a tool named `price_of`.
- A bad item produces a retry prompt that contains `Unknown item, try one of:` and the real item names.
- The final answer contains the price from the `Deps` you passed in.

Press **Check my work** when you are ready. If a test fails, read its message and the lesson sections "Choosing the decorator" and "Asking the model to retry".
