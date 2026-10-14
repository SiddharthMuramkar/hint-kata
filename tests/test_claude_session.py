import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.traces import Trace, public_view
from tests.test_traces import script

HOOK = Path(__file__).parent.parent / ".claude" / "hooks" / "session_end.py"
SECRET = "sk-abcdef1234567890XYZ"


def transcript(tmp_path: Path) -> Path:
    def msg(role: str, content: object, **extra: object) -> dict[str, object]:
        return {"type": role, "message": {"role": role, "content": content}, **extra}

    lines = [
        json.dumps({"type": "queue-operation", "content": "dropped"}),
        json.dumps(
            msg("user", "Please fix /Users/alice/proj/x.py, mail bob@example.com", version="9.9.9")
            | {"timestamp": "2026-10-01T10:00:00Z"}
        ),
        "{not json",
        json.dumps(msg("assistant", [{"type": "thinking", "thinking": "secret thoughts"}])),
        json.dumps(msg("assistant", [{"type": "text", "text": "x" * 700}])),
        json.dumps(
            msg(
                "assistant",
                [
                    {"type": "tool_use", "name": "Bash", "input": {"command": f"echo {SECRET}"}},
                    {
                        "type": "tool_use",
                        "name": "Edit",
                        "input": {"file_path": "/home/bob/a/b.py"},
                    },
                    {"type": "tool_use", "name": "Grep", "input": {"pattern": "p"}},
                ],
            )
        ),
        json.dumps({"type": "attachment", "attachment": {"content": "dropped"}}),
        json.dumps(
            msg(
                "user",
                [
                    {"type": "tool_result", "content": [{"type": "text", "text": "ok"}]},
                    {"type": "tool_result", "content": [{"type": "image", "source": {}}]},
                ],
            )
        ),
    ]
    path = tmp_path / "abcdef12-0000.jsonl"
    path.write_text("\n".join(lines) + "\n")
    return path


def test_normalise_whitelists_and_redacts(tmp_path: Path) -> None:
    mod = script("claude_session")
    trace = mod.normalise(transcript(tmp_path))
    Trace.model_validate_json(trace.model_dump_json())
    assert trace.kind == "claude_code_session"
    assert [s.kind for s in trace.steps] == [
        "user_prompt",
        "model_request",
        "tool_call",
        "tool_call",
        "tool_call",
        "tool_result",
        "tool_result",
    ]
    assert [s.idx for s in trace.steps] == list(range(7))
    dump = trace.model_dump_json()
    assert "~/proj/x.py" in dump
    assert "[redacted]" in dump
    assert SECRET not in dump and "example.com" not in dump and "alice" not in dump
    assert "secret thoughts" not in dump and "dropped" not in dump
    assert len(trace.steps[1].summary) <= 600
    assert [s.title for s in trace.steps[2:5]] == ["Bash", "Edit", "Grep"]
    assert trace.steps[3].summary == "b.py"
    assert trace.steps[6].summary == "[binary/omitted]"
    assert trace.source == {
        "generator": "claude-code",
        "claude_code_version": "9.9.9",
        "captured_at": "2026-10-01",
        "redaction": {"ruleset_version": 1, "human_reviewed": False},
    }
    assert trace.takeaways == [] and all(s.checkpoint is None for s in trace.steps)
    assert public_view(trace)


@pytest.mark.parametrize(
    "text",
    [
        "ghp_" + "a1B2c3D4e5F6",
        "AKIA" + "ABCDEFGHIJKLMNOP",
        "Authorization: Bearer abc.def",
        "API_TOKEN=hunter2",
        "a" * 8 + "0123456789abcdef" * 2,
    ],
)
def test_secret_shapes(text: str) -> None:
    out = script("claude_session").redact(text)
    assert "[redacted]" in out
    assert "hunter2" not in out and "abc.def" not in out


def test_plain_paths_survive() -> None:
    text = "docs/learning-log/057-session-traces.md"
    assert script("claude_session").redact(text) == text


def test_cli_deterministic_with_pr_steps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mod = script("claude_session")
    src = transcript(tmp_path)

    def fake_build(repo: str, number: int) -> Trace:
        base = mod.normalise(src)
        return base.model_copy(
            update={"steps": [base.steps[0].model_copy(update={"kind": "merge"})]}
        )

    monkeypatch.setattr(mod.pr_timeline, "build", fake_build)
    outs = [tmp_path / "a.json", tmp_path / "b.json"]
    for out in outs:
        monkeypatch.setattr(
            sys,
            "argv",
            ["x", "--transcript", str(src), "--repo", "o/r", "--pr", "1", "--out", str(out)],
        )
        mod.main()
    assert outs[0].read_text() == outs[1].read_text()
    trace = Trace.model_validate_json(outs[0].read_text())
    assert trace.steps[-1].kind == "merge" and trace.steps[-1].idx == len(trace.steps) - 1


def run_hook(tmp_path: Path, stdin: str) -> subprocess.CompletedProcess[str]:
    env = {"HOME": str(tmp_path / "home"), "PATH": "/usr/bin:/bin"}
    return subprocess.run(
        [sys.executable, str(HOOK)], input=stdin, text=True, capture_output=True, env=env
    )


def test_hook_copies_and_never_overwrites(tmp_path: Path) -> None:
    src = tmp_path / "t.jsonl"
    src.write_text("one\n")
    payload = json.dumps({"session_id": "sess-1", "transcript_path": str(src)})
    assert run_hook(tmp_path, payload).returncode == 0
    dest = tmp_path / "home" / "hint-kata-inbox" / "sess-1.jsonl"
    assert dest.read_text() == "one\n"
    src.write_text("two\n")
    assert run_hook(tmp_path, payload).returncode == 0
    assert dest.read_text() == "one\n"


@pytest.mark.parametrize("stdin", ["", "not json", "{}", '{"transcript_path": "/nope/x.jsonl"}'])
def test_hook_exits_zero_on_bad_input(tmp_path: Path, stdin: str) -> None:
    assert run_hook(tmp_path, stdin).returncode == 0
