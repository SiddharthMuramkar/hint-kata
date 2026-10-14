"""Hidden checks: the learner's test_items.py must pass on good_app and fail on buggy_app."""

import ast
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path(os.getcwd())
LEARNER_FILE = WORKSPACE / "test_items.py"


def _run(app_module: str) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["APP_MODULE"] = app_module
    env["PYTHONPATH"] = str(WORKSPACE)
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(LEARNER_FILE)]
    return subprocess.run(
        cmd, cwd=WORKSPACE, env=env, capture_output=True, text=True, timeout=100
    )


def _count_tests(source: str) -> int:
    tree = ast.parse(source)
    return sum(
        isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith("test")
        for node in ast.walk(tree)
    )


def test_file_has_at_least_three_tests() -> None:
    assert LEARNER_FILE.exists(), "test_items.py is missing from the workspace"
    count = _count_tests(LEARNER_FILE.read_text(encoding="utf-8"))
    assert count >= 3, f"found {count} test function(s) in test_items.py, need at least 3"


def test_learner_tests_pass_on_good_app() -> None:
    proc = _run("good_app")
    assert proc.returncode == 0, "your tests should pass on good_app:\n" + proc.stdout[-1500:]


def test_learner_tests_fail_on_buggy_app() -> None:
    proc = _run("buggy_app")
    assert proc.returncode != 0, (
        "your tests also pass on buggy_app, so they do not catch its bugs. "
        "Add tests for the missing 404 and the missing price rule."
    )
    # A broken import is not a caught bug: we need a real test failure, not a collection error.
    assert "failed" in proc.stdout, "the run on buggy_app did not report a failed test:\n" + (
        proc.stdout[-1500:]
    )
