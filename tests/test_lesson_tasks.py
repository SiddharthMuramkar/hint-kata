"""Every lesson task's hidden tests must pass on its solution and fail on its starter.

This runs the same command as app/checker.py: pytest in a subprocess, with the workspace on
PYTHONPATH. It is generic, so later lessons only need to add their `task/` folders.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CONTENT = Path(__file__).resolve().parent.parent / "content"
TIMEOUT = 120

TASK_DIRS = sorted(
    p
    for p in CONTENT.glob("*/*/task")
    if (p / "starter").is_dir() and (p / "solution").is_dir() and (p / "tests").is_dir()
)


def _run_hidden_tests(
    task_dir: Path, source: Path, workspace: Path
) -> subprocess.CompletedProcess[str]:
    shutil.copytree(source, workspace)
    # Like the real checker: no API keys, so a test that needs a live model cannot pass by luck.
    env = {
        k: v
        for k, v in os.environ.items()
        if not any(word in k.upper() for word in ("KEY", "TOKEN", "SECRET"))
    }
    env["PYTHONPATH"] = str(workspace)
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    cmd.append(str(task_dir / "tests"))
    return subprocess.run(
        cmd, cwd=workspace, env=env, capture_output=True, text=True, timeout=TIMEOUT
    )


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.parent.name)
def test_solution_passes_hidden_tests(task_dir: Path, tmp_path: Path) -> None:
    proc = _run_hidden_tests(task_dir, task_dir / "solution", tmp_path / "ws")
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.parent.name)
def test_starter_fails_hidden_tests(task_dir: Path, tmp_path: Path) -> None:
    proc = _run_hidden_tests(task_dir, task_dir / "starter", tmp_path / "ws")
    assert proc.returncode != 0, "the starter already passes the hidden tests"
