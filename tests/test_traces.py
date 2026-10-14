import importlib.util
import json
import os
import stat
import sys
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.traces import Trace, grade, load_trace, public_view

ROOT = Path(__file__).parent
FIXTURES = ROOT / "fixtures" / "content"
SCRIPTS = ROOT.parent / "traces" / "scripts"


def script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("HINTKATA_CONTENT_ROOT", str(FIXTURES))
    return TestClient(app)


def test_load_and_validate() -> None:
    trace = load_trace("fx-trace", FIXTURES)
    assert trace is not None
    assert [s.kind for s in trace.steps] == ["user_prompt", "tool_call"]
    assert load_trace("missing", FIXTURES) is None
    assert load_trace("../fx-trace", FIXTURES) is None


def test_model_rejects_unknown_kind() -> None:
    data = json.loads((FIXTURES / "fastapi/fx-trace/trace.json").read_text())
    data["kind"] = "video"
    with pytest.raises(ValidationError):
        Trace.model_validate(data)


def test_public_view_strips_answers() -> None:
    trace = load_trace("fx-trace", FIXTURES)
    assert trace is not None
    view = public_view(trace)
    text = json.dumps(view)
    assert "Instructions say never to guess" not in text
    assert '"answer"' not in text
    assert "Call a tool" in text  # options stay
    # The original model keeps its answer.
    assert trace.steps[1].checkpoint and trace.steps[1].checkpoint.answer == 1


def test_grade() -> None:
    trace = load_trace("fx-trace", FIXTURES)
    assert trace is not None
    assert grade(trace, 1, 1) == (True, "Instructions say never to guess.")
    assert grade(trace, 1, 0)[0] is False
    with pytest.raises(KeyError):
        grade(trace, 0, 0)  # step without a checkpoint


def test_routes(client: TestClient) -> None:
    r = client.get("/api/trace/fx-trace")
    assert r.status_code == 200
    assert "answer" not in r.text and "explanation" not in r.text
    assert client.get("/api/trace/nope").status_code == 404
    ok = client.post("/api/trace/fx-trace/1", json={"choice": 1})
    assert ok.json() == {"correct": True, "explanation": "Instructions say never to guess."}
    assert client.post("/api/trace/fx-trace/1", json={"choice": 0}).json()["correct"] is False
    assert client.post("/api/trace/fx-trace/0", json={"choice": 0}).status_code == 404
    assert client.post("/api/trace/nope/1", json={"choice": 0}).status_code == 404
    assert client.post("/api/trace/fx-trace/1", json={"choice": "x"}).status_code == 422


def test_agent_run_script_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = script("agent_run")
    outs = [tmp_path / "a.json", tmp_path / "b.json"]
    for out in outs:
        monkeypatch.setattr(sys, "argv", ["agent_run.py", "--out", str(out)])
        module.main()
    assert outs[0].read_bytes() == outs[1].read_bytes()
    trace = Trace.model_validate_json(outs[0].read_text())
    assert [s.kind for s in trace.steps] == [
        "user_prompt",
        "instructions",
        "model_request",
        "tool_call",
        "retry",
        "model_request",
        "tool_call",
        "tool_result",
        "model_request",
        "final_output",
    ]
    assert [s.idx for s in trace.steps if s.checkpoint] == [2, 3]
    assert trace.steps[-1].metrics["requests"] == 3
    assert trace.source["generator"] == "FunctionModel"


# `gh api <path>` prints the file named after the path (with / ? = turned into _).
FAKE_GH = """#!/bin/sh
cat "$FAKE_DIR/$(printf '%s' "$2" | tr '/?=' '___')"
"""


def canned(conclusion: str) -> dict[str, object]:
    pr = {
        "title": "Add thing",
        "user": {"login": "ann"},
        "head": {"sha": "abc1234"},
        "base": {"ref": "main"},
        "merged": True,
        "merged_by": {"login": "bob"},
        "changed_files": 2,
        "additions": 10,
        "deletions": 1,
        "html_url": "https://github.com/o/r/pull/7",
    }
    commit = {
        "sha": "1111111aaaa",
        "commit": {"message": "feat: a\n\nSECRETBODY", "author": {"name": "Ann"}},
    }
    review = {"state": "APPROVED", "body": "LGTM", "user": {"login": "bob"}}
    run = {"name": "ci", "status": "completed", "conclusion": conclusion}
    return {
        "repos_o_r_pulls_7": pr,
        "repos_o_r_pulls_7_commits_per_page_100": [commit],
        "repos_o_r_pulls_7_reviews_per_page_100": [review],
        "repos_o_r_commits_abc1234_check-runs": {"check_runs": [run]},
    }


@pytest.mark.parametrize(("conclusion", "answer"), [("success", 0), ("failure", 1)])
def test_pr_timeline_with_fake_gh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conclusion: str, answer: int
) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_DIR", str(tmp_path))
    for name, payload in canned(conclusion).items():
        (tmp_path / name).write_text(json.dumps(payload))
    out = tmp_path / "pr.json"
    monkeypatch.setattr(
        sys, "argv", ["pr_timeline.py", "--repo", "o/r", "--pr", "7", "--out", str(out)]
    )
    script("pr_timeline").main()
    trace = Trace.model_validate_json(out.read_text())
    assert trace.kind == "github_pr"
    assert [s.kind for s in trace.steps] == [
        "git_commit",
        "pr_opened",
        "ci_check",
        "review_comment",
        "merge",
    ]
    assert trace.steps[0].summary == "feat: a"
    checkpoint = trace.steps[-1].checkpoint
    assert checkpoint and checkpoint.answer == answer
    assert "SECRETBODY" not in out.read_text()  # only the headline is kept


def test_partial_renders_only_with_trace() -> None:
    from app.main import templates

    render = templates.get_template("partials/trace.html").render
    assert render(has_trace=False, lesson_id="x").strip() == ""
    html = render(has_trace=True, lesson_id="fx-trace", url_for=lambda _n, path: f"/static/{path}")
    assert '<section id="trace" data-lesson="fx-trace">' in html
    assert "/static/js/trace.js" in html
