"""Task: write tests for support_agent. Run them with `uv run pytest -q test_support_agent.py`."""

import pytest  # noqa: F401  (you will use these)
from pydantic_ai import capture_run_messages, models  # noqa: F401
from pydantic_ai.messages import (  # noqa: F401
    ModelMessage,
    ModelResponse,
    RetryPromptPart,
    ToolCallPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel  # noqa: F401
from pydantic_ai.models.test import TestModel  # noqa: F401
from support_agent import SupportDeps, SupportReply, support_agent  # noqa: F401

# TODO 1: block real model requests for every test in this file (`models.ALLOW_MODEL_REQUESTS`).

# TODO 2: a test that runs the agent with TestModel inside `capture_run_messages()` and asserts
# the order of the tool calls: lookup_order first, then refund.
# TestModel makes up its arguments, so give SupportDeps an order whose id is what it invents.

# TODO 3: a test with a scripted FunctionModel for the happy path:
# lookup_order, then refund, then the final answer. Assert the output and `deps.refunds`.

# TODO 4: a test where the scripted model calls refund BEFORE lookup_order.
# The agent must reject it with a retry prompt, and the order must be refunded only once.

# TODO 5: a test where the scripted model looks up an unknown order, gets the retry prompt,
# and then recovers. Assert the text of the retry prompt.

# TODO 6: a test that asserts `result.usage.requests` and `result.usage.tool_calls`.
