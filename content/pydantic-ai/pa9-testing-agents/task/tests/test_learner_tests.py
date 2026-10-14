"""Hidden checks: the learner's tests must pass on support_agent and fail on a buggy copy of it.

The learner's file imports `support_agent`. To run it against the buggy copy we start a child
pytest whose `support_agent` import is replaced by `buggy_support_agent` (a `sys.modules` swap
made before the learner's file is imported).
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = Path(os.getcwd())
LEARNER_FILE = WORKSPACE / "test_support_agent.py"
MIN_TESTS = 5

# Runs in the child process. argv[1] is the learner's test file.
DRIVER = """
import sys

import pytest

import buggy_support_agent

sys.modules["support_agent"] = buggy_support_agent  # the learner's import now gets the buggy copy
sys.exit(pytest.main(["-q", "-p", "no:cacheprovider", sys.argv[1]]))
"""


def _env() -> dict[str, str]:
    env = {
        k: v
        for k, v in os.environ.items()
        if not any(word in k.upper() for word in ("KEY", "TOKEN", "SECRET"))
    }
    env["PYTHONPATH"] = os.pathsep.join([str(WORKSPACE), str(HERE)])
    return env


def _run_on_good_agent() -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(LEARNER_FILE)]
    return subprocess.run(
        cmd, cwd=WORKSPACE, env=_env(), capture_output=True, text=True, timeout=100
    )


def _run_on_buggy_agent() -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-c", DRIVER, str(LEARNER_FILE)]
    return subprocess.run(
        cmd, cwd=WORKSPACE, env=_env(), capture_output=True, text=True, timeout=100
    )


def _count_tests(source: str) -> int:
    tree = ast.parse(source)
    return sum(
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test")
        for node in ast.walk(tree)
    )


def test_file_has_enough_tests() -> None:
    assert LEARNER_FILE.exists(), "test_support_agent.py is missing from the workspace"
    count = _count_tests(LEARNER_FILE.read_text(encoding="utf-8"))
    assert count >= MIN_TESTS, f"found {count} test function(s), need at least {MIN_TESTS}"


def test_real_model_requests_are_blocked() -> None:
    sources = [LEARNER_FILE, WORKSPACE / "conftest.py"]
    text = "\n".join(p.read_text(encoding="utf-8") for p in sources if p.exists())
    assert re.search(r"ALLOW_MODEL_REQUESTS\s*=\s*False", text), (
        "set `models.ALLOW_MODEL_REQUESTS = False` in your test file (or a conftest.py)"
    )


def test_learner_tests_pass_on_the_good_agent() -> None:
    proc = _run_on_good_agent()
    assert proc.returncode == 0, "your tests should pass on support_agent:\n" + proc.stdout[-1500:]


def test_learner_tests_fail_on_the_buggy_agent() -> None:
    proc = _run_on_buggy_agent()
    assert proc.returncode != 0, (
        "your tests also pass on the buggy agent, so they do not catch its bug. "
        "In the buggy copy, refund can run before lookup_order. "
        "Test the order of the tool calls, and what happens when refund comes first."
    )
    # A broken import is not a caught bug: we need a real test failure, not a collection error.
    assert re.search(r"\d+ failed", proc.stdout), (
        "the run on the buggy agent did not report a failed test:\n" + proc.stdout[-1500:]
    )
