---
name: stop-run-tests
enabled: true
event: stop
action: block
conditions:
  - field: transcript
    operator: not_contains
    pattern: pytest
---
Blocked: run `uv run pytest -q` (and ruff, ty) before you stop, and show the result.
