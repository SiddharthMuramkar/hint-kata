import shutil
import stat
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import checker
from app.config import settings
from app.main import app

FIXTURE = Path(__file__).parent / "fixtures" / "checker" / "task"


@pytest.fixture
def content(tmp_path: Path) -> Path:
    """A content tree with one lesson whose task is the fixture."""
    root = tmp_path / "content"
    shutil.copytree(FIXTURE, root / "track" / "lesson-a" / "task")
    return root


def test_find_task_dir(content: Path) -> None:
    assert checker.find_task_dir("lesson-a", content) == content / "track" / "lesson-a" / "task"
    assert checker.find_task_dir("nope", content) is None


def test_workspace_is_copied_once_and_never_overwritten(content: Path, tmp_path: Path) -> None:
    task = content / "track" / "lesson-a" / "task"
    root = tmp_path / "workspace"
    ws = checker.prepare_workspace("lesson-a", task, root)
    assert ws == root / "lesson-a"
    (ws / "solution.py").write_text("# mine\n")
    assert checker.prepare_workspace("lesson-a", task, root) == ws
    assert (ws / "solution.py").read_text() == "# mine\n"


def test_pytest_check_fails_on_starter_and_passes_when_fixed(content: Path, tmp_path: Path) -> None:
    task = content / "track" / "lesson-a" / "task"
    ws = checker.prepare_workspace("lesson-a", task, tmp_path / "workspace")
    bad = checker.run_pytest_check(task, ws)
    assert not bad.passed and bad.kind == "pytest"
    assert "assert" in bad.output
    (ws / "solution.py").write_text("def add(a: int, b: int) -> int:\n    return a + b\n")
    assert checker.run_pytest_check(task, ws).passed


def test_pytest_check_hides_secrets_from_learner_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    task, ws = tmp_path / "task", tmp_path / "ws"
    (task / "tests").mkdir(parents=True)
    ws.mkdir()
    (task / "tests" / "test_env.py").write_text(
        "import os\n\ndef test_env():\n    assert not any('KEY' in k.upper() for k in os.environ)\n"
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "x")
    monkeypatch.setenv("openrouter_api_key", "x")
    assert checker.run_pytest_check(task, ws).passed


def test_pytest_check_times_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    task, ws = tmp_path / "task", tmp_path / "ws"
    (task / "tests").mkdir(parents=True)
    ws.mkdir()
    (task / "tests" / "test_slow.py").write_text(
        "import time\n\ndef test_slow():\n    time.sleep(30)\n"
    )
    monkeypatch.setattr(checker, "PYTEST_TIMEOUT", 1)
    r = checker.run_pytest_check(task, ws)
    assert not r.passed
    assert r.output.endswith("Timed out after 1 s")


@pytest.fixture
def gh_task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake `gh` on PATH that prints its arguments joined by spaces."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text('#!/bin/sh\necho "args: $*"\n')
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")
    task = tmp_path / "gh-task"
    task.mkdir()
    (task / "check.yaml").write_text(
        "checks:\n"
        "  - name: exact\n"
        "    args: [api, 'repos/{repo}']\n"
        "    expect: 'args: api repos/me/practice'\n"
        "  - name: regex\n"
        "    args: [api, 'repos/{repo}/pulls', --jq, '.[0].number']\n"
        "    expect: 're:args: api repos/me/practice/pulls --jq .+'\n"
    )
    return task


def test_gh_checks_pass(gh_task: Path) -> None:
    r = checker.run_gh_checks(gh_task, "me/practice")
    assert r.passed and r.kind == "gh"
    assert r.output.splitlines()[0] == "✓ exact — got: args: api repos/me/practice"
    assert r.output.splitlines()[1].startswith("✓ regex")


def test_gh_checks_fail_when_a_check_differs(gh_task: Path) -> None:
    r = checker.run_gh_checks(gh_task, "me/other")
    assert not r.passed
    assert r.output.splitlines()[0].startswith("✗ exact")
    assert r.output.splitlines()[1].startswith("✗ regex")


def test_gh_checks_need_practice_repo(gh_task: Path) -> None:
    r = checker.run_gh_checks(gh_task, "")
    assert not r.passed and r.output == "Set PRACTICE_REPO in .env"


@pytest.fixture
def client(tmp_path: Path, content: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "hintkata_db_path", str(tmp_path / "t.db"))
    monkeypatch.setattr(settings, "content_root", str(content))
    monkeypatch.chdir(tmp_path)  # workspace/ is created here
    with TestClient(app) as c:
        yield c


def test_check_endpoints(client: TestClient) -> None:
    assert client.get("/api/check/lesson-a").json() == {"passed": None}
    r = client.post("/api/check/lesson-a")
    assert r.status_code == 200
    body = r.json()
    assert body["passed"] is False and body["kind"] == "pytest"
    last = client.get("/api/check/lesson-a").json()
    assert last == {"passed": False, "output": body["output"]}
    (Path("workspace") / "lesson-a" / "solution.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n"
    )
    assert client.post("/api/check/lesson-a").json()["passed"] is True
    assert client.get("/api/check/lesson-a").json()["passed"] is True


def test_check_endpoint_without_task(client: TestClient) -> None:
    r = client.post("/api/check/unknown")
    assert r.json()["passed"] is False and r.json()["kind"] == "none"
    assert client.get("/api/check/unknown").json() == {"passed": None}


def test_bad_lesson_id_is_404(client: TestClient) -> None:
    assert client.post("/api/check/%2E%2E").status_code == 404
    assert client.get("/api/check/%2E%2E").status_code == 404
    assert client.post("/api/check/Bad_ID").status_code == 404
