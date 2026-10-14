# Python

- Python 3.13, managed by uv. Run tools with `uv run`. Never use pip.
- ruff, line length 100. Full type hints on every function; `ty check` must pass.
- Tests use pytest. Tests never call a real model: set `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False` in `tests/conftest.py` and use `TestModel` or `FunctionModel` through `agent.override(model=...)`.
- Every new behaviour gets a test in the same PR. Prefer small functions and plain data over classes.
