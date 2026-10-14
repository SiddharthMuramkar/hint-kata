"""Hands-on checks: hidden pytest tests (code lessons) and read-only `gh` calls (GitHub lessons)."""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.config import Settings
from app.store import Store

PYTEST_TIMEOUT = 120
GH_TIMEOUT = 30
LESSON_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


@dataclass
class CheckResult:
    passed: bool
    output: str
    kind: str


def valid_lesson_id(lesson_id: str) -> bool:
    return LESSON_ID_RE.fullmatch(lesson_id) is not None


def validate_lesson_id(lesson_id: str) -> str:
    if not valid_lesson_id(lesson_id):
        raise ValueError(f"Invalid lesson id: {lesson_id!r}")
    return lesson_id


def _inside(path: Path, root: Path) -> Path:
    """Resolve `path` and refuse it unless it stays under `root`."""
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"{path} is outside {root}")
    return resolved


def find_task_dir(lesson_id: str, content_root: Path = Path("content")) -> Path | None:
    validate_lesson_id(lesson_id)
    task_dir = next(iter(sorted(content_root.glob(f"*/{lesson_id}/task"))), None)
    return None if task_dir is None else _inside(task_dir, content_root)


def prepare_workspace(
    lesson_id: str, task_dir: Path, workspace_root: Path = Path("workspace")
) -> Path:
    """Copy starter/ once; never overwrite the learner's work."""
    validate_lesson_id(lesson_id)
    workspace = _inside(workspace_root / lesson_id, workspace_root)
    if not workspace.exists():
        shutil.copytree(_inside(task_dir / "starter", task_dir), workspace)
    return workspace


def _text(data: str | bytes | None) -> str:
    return data.decode(errors="replace") if isinstance(data, bytes) else (data or "")


def run_pytest_check(task_dir: Path, workspace: Path) -> CheckResult:
    # The learner's code runs on their own machine, but keep API keys out of it.
    env = {
        k: v
        for k, v in os.environ.items()
        if not any(word in k.upper() for word in ("KEY", "TOKEN", "SECRET"))
    }
    env["PYTHONPATH"] = str(workspace.resolve())
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    cmd.append(str(_inside(task_dir / "tests", task_dir)))
    try:
        proc = subprocess.run(
            cmd, cwd=workspace, env=env, capture_output=True, text=True, timeout=PYTEST_TIMEOUT
        )
    except subprocess.TimeoutExpired as e:
        out = _text(e.stdout) + _text(e.stderr)
        return CheckResult(False, out[-3900:] + f"\nTimed out after {PYTEST_TIMEOUT} s", "pytest")
    return CheckResult(proc.returncode == 0, (proc.stdout + proc.stderr)[-4000:], "pytest")


def _gh_line(check: dict[str, Any], repo: str) -> tuple[bool, str]:
    name = str(check["name"])
    args = [str(a).replace("{repo}", repo) for a in check["args"]]
    expect = str(check["expect"])
    try:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=GH_TIMEOUT)
    except FileNotFoundError:
        return False, f"✗ {name} — gh is not installed"
    except subprocess.TimeoutExpired:
        return False, f"✗ {name} — timed out after {GH_TIMEOUT} s"
    got = proc.stdout.strip()
    if expect.startswith("re:"):
        ok = re.fullmatch(expect[3:], got) is not None
    else:
        ok = got == expect
    return ok, f"{'✓' if ok else '✗'} {name} — got: {got or proc.stderr.strip()[:200]}"


def run_gh_checks(task_dir: Path, repo: str) -> CheckResult:
    if not repo:
        return CheckResult(False, "Set PRACTICE_REPO in .env", "gh")
    checks = yaml.safe_load((task_dir / "check.yaml").read_text())["checks"]
    results = [_gh_line(c, repo) for c in checks]
    return CheckResult(all(ok for ok, _ in results), "\n".join(line for _, line in results), "gh")


def run_check(lesson_id: str, settings: Settings, store: Store, user_id: int) -> CheckResult:
    task_dir = (
        find_task_dir(lesson_id, Path(settings.content_root))
        if valid_lesson_id(lesson_id)
        else None
    )
    if task_dir and (task_dir / "tests").is_dir():
        result = run_pytest_check(task_dir, prepare_workspace(lesson_id, task_dir))
    elif task_dir and (task_dir / "check.yaml").is_file():
        result = run_gh_checks(task_dir, settings.practice_repo)
    else:
        return CheckResult(False, "This lesson has no hands-on task.", "none")
    store.add_check(user_id, lesson_id, result.passed, result.output)
    return result
