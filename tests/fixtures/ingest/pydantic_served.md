> ## Documentation Index
> Fetch the complete documentation index at: https://example.com/llms.txt

## Querying This Documentation

**warning**: agent query parameters (`intent`, `stack` and `harness`) not included.

Include these query parameters when fetching any page: `intent`, `stack`, `harness`.

---

# Installation

Pydantic AI is available on PyPI, so installation is as simple as:

-   [pip](#tab-panel-323)
-   [uv](#tab-panel-324)

Terminal

```bash
pip install pydantic-ai
```

Terminal

```bash
uv add pydantic-ai
```

!!! note "Heads up"
    Requires Python 3.11+.

    ```python
    # a comment inside an indented fence
    print("hi")
    ```

Next paragraph after the note.

## Defining an agent {#defining-an-agent}

See [`Agent`][pydantic_ai.agent.Agent] and the [guide](https://example.com/guide).

=== "Python"

    Use the class directly.

=== "CLI"

    Run `clai` instead.

```python {title="run_agent.py" requires="x.py"}
from pydantic_ai import Agent

agent = Agent("test")
```

::: pydantic_ai.agent.Agent
    options:
      show_source: false

```snippet
docs/examples/hello.py
```

## Slim install

Use `pydantic-ai-slim`.
