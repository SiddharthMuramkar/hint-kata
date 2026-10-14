"""SPEC section 23 rows: Hands-on, Traces.

Python tasks: tests/test_lesson_tasks.py already runs the hidden tests against every
`task/solution` (must pass) and `task/starter` (must fail), and tests/test_checker.py covers the
timeout. `traces/scripts/pr_timeline.py` needs `gh`, so tests/test_traces.py re-runs it with a
fake `gh` and canned JSON; that is not repeated
here. Here: the GitHub `check.yaml` tasks, and the trace lessons.
"""

import importlib.util
import json
import stat
import sys
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.checker import run_gh_checks
from app.config import settings
from app.content import Lesson
from app.traces import Trace, load_trace

from .conftest import LESSONS, ROOT, lessons_with

GH = [pytest.param(x, id=x.id) for x in LESSONS.values() if x.task_kind == "gh"]
TRACES = lessons_with("has_trace")


@pytest.fixture
def fake_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A `gh` on PATH that prints 1 and succeeds, so no network is touched."""
    gh = tmp_path / "bin" / "gh"
    gh.parent.mkdir()
    gh.write_text("#!/bin/sh\necho 1\n")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{gh.parent}:/usr/bin:/bin")


def task_dir(lesson: Lesson) -> Path:
    return lesson.dir / "task"


@pytest.mark.parametrize("lesson", GH)
def test_gh_checks_show_one_result_per_check(fake_gh: None, lesson: Lesson) -> None:
    checks = yaml.safe_load((task_dir(lesson) / "check.yaml").read_text())["checks"]
    r = run_gh_checks(task_dir(lesson), "me/practice")
    lines = r.output.splitlines()
    assert r.kind == "gh" and len(lines) == len(checks)
    assert all(line[0] in "✓✗" and c["name"] in line for line, c in zip(lines, checks, strict=True))
    assert run_gh_checks(task_dir(lesson), "").output == "Set PRACTICE_REPO in .env"


@pytest.mark.parametrize("lesson", GH)
def test_check_endpoint_shows_gh_output(
    client: TestClient, fake_gh: None, monkeypatch: pytest.MonkeyPatch, lesson: Lesson
) -> None:
    monkeypatch.setattr(settings, "practice_repo", "me/practice")
    body = client.post(f"/api/check/{lesson.id}").json()
    assert body["kind"] == "gh" and any(ch in body["output"] for ch in "✓✗")
    assert client.get(f"/api/check/{lesson.id}").json()["output"] == body["output"]


@pytest.mark.parametrize("lesson", TRACES)
def test_trace_plays_and_hides_answers(client: TestClient, lesson: Lesson) -> None:
    trace = load_trace(lesson.id, ROOT / "content")
    assert isinstance(trace, Trace) and trace.steps
    view = client.get(f"/api/trace/{lesson.id}").json()
    assert [s["idx"] for s in view["steps"]] == [s.idx for s in trace.steps]
    for step in view["steps"]:
        assert not {"answer", "explanation"} & (step["checkpoint"] or {}).keys()


@pytest.mark.parametrize("lesson", TRACES)
def test_trace_checkpoints_are_graded(client: TestClient, lesson: Lesson) -> None:
    trace = load_trace(lesson.id, ROOT / "content")
    assert trace
    step = next(s for s in trace.steps if s.checkpoint)
    cp = step.checkpoint
    assert cp
    url = f"/api/trace/{lesson.id}/{step.idx}"
    good = client.post(url, json={"choice": cp.answer}).json()
    bad = client.post(url, json={"choice": (cp.answer + 1) % len(cp.options)}).json()
    assert good == {"correct": True, "explanation": cp.explanation}
    assert bad["correct"] is False


def test_agent_run_script_reproduces_the_committed_trace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    committed = ROOT / "content/pydantic-ai/pa2-tools-deps/trace.json"
    if not committed.exists():
        pytest.skip("lesson pa2-tools-deps has no trace.json")
    path = ROOT / "traces/scripts/agent_run.py"
    spec = importlib.util.spec_from_file_location("agent_run", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    out = tmp_path / "trace.json"
    monkeypatch.setattr(sys, "argv", ["agent_run.py", "--out", str(out)])
    module.main()
    # Step structure only: `source` holds today's date and the installed library version.
    regenerated = json.loads(out.read_text())["steps"]
    assert regenerated == json.loads(committed.read_text())["steps"]
