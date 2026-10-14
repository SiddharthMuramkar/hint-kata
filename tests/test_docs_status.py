"""Unit tests for scripts/docs_status.py. The PR list is a recorded fixture; no test calls gh."""

import importlib.util
import json
import re
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "docs_status.py"
FIXTURE = Path(__file__).resolve().parent / "fixtures" / "docs_status" / "merged_prs.json"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("docs_status", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ds = _load()

# One file per fixture PR that owns one. PR #29 (docs only) owns none.
FILES = [
    "001-harness.md",
    "002-app-skeleton.md",
    "011-fetch-docs.md",
    "020-docs-pass.md",
    "021-mastery.md",
    "053-docs-ingestion.md",
    "063-reveal-retest.md",
    "069-hookify-false-positives.md",
]


def _merged() -> list[dict[str, Any]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _repo(root: Path, files: list[str] = FILES, log: str | None = None) -> Path:
    logs = root / "docs" / "learning-log"
    logs.mkdir(parents=True)
    for name in files:
        (logs / name).write_text("entry\n", encoding="utf-8")
    if log is not None:
        (root / "docs" / "LEARNING_LOG.md").write_text(log, encoding="utf-8")
    return root


def _index(root: Path, prs: list[dict[str, Any]] | None = None, old: str = "") -> str:
    return ds.build_index(prs or _merged(), root / "docs" / "learning-log", old)


def _pr_numbers(index: str) -> list[int]:
    return [int(n) for n in re.findall(r"^\| #(\d+) \|", index, re.M)]


def test_rows_follow_merge_time_not_pr_number(tmp_path: Path) -> None:
    index = _index(_repo(tmp_path))
    assert index.startswith(ds.HEADER)
    # #22 merged after #23 and #25; #69 merged before #66; #76 merged after both.
    assert _pr_numbers(index) == [23, 25, 22, 40, 69, 66, 76, 105]


def test_closes_line_then_pr_number_picks_the_file(tmp_path: Path) -> None:
    index = _index(_repo(tmp_path))
    assert (
        "| #22 | [001 — Claude Code harness](learning-log/001-harness.md) |" in index
    )  # Closes #1
    assert "learning-log/063-reveal-retest.md) |" in index  # #66 Closes #63
    assert "| #69 | [069 — tighten hookify" in index  # no Closes line: the PR number itself
    assert "| #105 | [053 — heading-aware chunking" in index  # prefix stripped, Closes #53


def test_pr_76_is_mapped_to_the_docs_pass_entry(tmp_path: Path) -> None:
    """PR #76 has no Closes line and 076 is not a file; OVERRIDES points it at 020."""
    index = _index(_repo(tmp_path))
    assert (
        "| #76 | [020 — phase 1 closed, phase 2 in flight](learning-log/020-docs-pass.md) |"
        in index
    )


def test_a_pr_without_an_entry_file_gets_no_row(tmp_path: Path) -> None:
    assert 29 not in _pr_numbers(_index(_repo(tmp_path)))


def test_rows_already_in_the_index_keep_their_text(tmp_path: Path) -> None:
    old = (
        ds.HEADER + "| #23 | [002 — App skeleton: FastAPI, dark theme, safe Markdown]"
        "(learning-log/002-app-skeleton.md) |\n"
        "| — | [020 — Docs pass: phase 1 closed, phase 2 opened](learning-log/020-docs-pass.md) |\n"
    )
    index = _index(_repo(tmp_path), old=old)
    assert (
        "| #23 | [002 — App skeleton: FastAPI, dark theme, safe Markdown]"
        "(learning-log/002-app-skeleton.md) |\n"
    ) in index
    # The old row had no PR number; the row now says #76 and keeps its label.
    assert (
        "| #76 | [020 — Docs pass: phase 1 closed, phase 2 opened](learning-log/020-docs-pass.md) |"
        in index
    )
    assert "| — |" not in index


def test_files_no_merged_pr_claims_are_listed_at_the_end(tmp_path: Path) -> None:
    root = _repo(tmp_path, [*FILES, "107-docs-status-script.md", "500-orphan.md"])
    index = _index(root)
    head, _, tail = index.partition("\n## Unmatched entries\n")
    assert _pr_numbers(head) == [23, 25, 22, 40, 69, 66, 76, 105]
    assert tail.endswith(
        "- [107-docs-status-script.md](learning-log/107-docs-status-script.md)\n"
        "- [500-orphan.md](learning-log/500-orphan.md)\n"
    )


def test_no_unmatched_section_when_every_file_is_claimed(tmp_path: Path) -> None:
    assert "Unmatched" not in _index(_repo(tmp_path))


def test_running_twice_changes_nothing(tmp_path: Path) -> None:
    root = _repo(tmp_path, [*FILES, "107-docs-status-script.md"])
    first = _index(root)
    assert _index(root, old=first) == first


def test_a_file_belongs_to_the_first_pr_that_claims_it(tmp_path: Path) -> None:
    prs = [
        {
            "number": 10,
            "title": "feat: first",
            "body": "Closes #5",
            "mergedAt": "2026-01-01T00:00:00Z",
        },
        {
            "number": 11,
            "title": "fix: follow-up",
            "body": "Closes #5",
            "mergedAt": "2026-01-02T00:00:00Z",
        },
    ]
    index = _index(_repo(tmp_path, ["005-thing.md"]), prs)
    assert _pr_numbers(index) == [10]


def test_a_pipe_in_a_title_does_not_break_the_table(tmp_path: Path) -> None:
    prs = [{"number": 7, "title": "feat: a | b", "body": None, "mergedAt": "2026-01-01T00:00:00Z"}]
    index = _index(_repo(tmp_path, ["007-pipes.md"]), prs)
    assert "| #7 | [007 — a \\| b](learning-log/007-pipes.md) |" in index


def test_check_fails_until_the_index_is_regenerated(tmp_path: Path) -> None:
    root = _repo(tmp_path, log="stale\n")
    fetch = {"merged": _merged()}.__getitem__
    log = root / "docs" / "LEARNING_LOG.md"
    assert ds.main(["--check"], root=root, fetch=fetch) == 1
    assert log.read_text(encoding="utf-8") == "stale\n"  # --check never writes
    assert ds.main(["--learning-log"], root=root, fetch=fetch) == 0
    assert log.read_text(encoding="utf-8").startswith(ds.HEADER)
    assert ds.main(["--check"], root=root, fetch=fetch) == 0


def test_learning_log_reports_rows_and_unmatched(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _repo(tmp_path, [*FILES, "107-docs-status-script.md"])
    fetch = {"merged": _merged()}.__getitem__
    ds.main(["--learning-log"], root=root, fetch=fetch)
    assert "8 rows, 1 unmatched, changed" in capsys.readouterr().out
    ds.main(["--learning-log"], root=root, fetch=fetch)
    assert "8 rows, 1 unmatched, unchanged" in capsys.readouterr().out


def test_progress_block(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for track, lessons in {"fastapi": ["fa1-a", "fa2-b"], "github": ["gh1-c"], "empty": []}.items():
        for name in lessons:
            (tmp_path / "content" / track / name).mkdir(parents=True)
            (tmp_path / "content" / track / name / "lesson.md").write_text("x", encoding="utf-8")
        (tmp_path / "content" / track).mkdir(parents=True, exist_ok=True)
    (tmp_path / "content" / "sources.yaml").write_text("sources: []\n", encoding="utf-8")  # a file
    data = {
        "open_prs": [{"number": 9, "title": "docs: thing", "headRefName": "docs-thing"}],
        "open_issues": [
            {"number": 30, "title": "Later", "milestone": None},
            {"number": 12, "title": "B", "milestone": {"title": "Phase 2"}},
            {"number": 5, "title": "A", "milestone": {"title": "Phase 2"}},
            {"number": 61, "title": "C", "milestone": {"title": "Phase 3"}},
        ],
    }
    assert ds.main(["--progress"], root=tmp_path, fetch=data.__getitem__) == 0
    assert capsys.readouterr().out == (
        "### Lessons on main\n"
        "- empty: 0\n"
        "- fastapi: 2\n"
        "- github: 1\n"
        "- total: 3\n"
        "\n"
        "### Open pull requests (1)\n"
        "- #9 docs: thing (`docs-thing`)\n"
        "\n"
        "### Open issues by milestone (4)\n"
        "\n"
        "#### Phase 2 (2)\n"
        "- #5 A\n"
        "- #12 B\n"
        "\n"
        "#### Phase 3 (1)\n"
        "- #61 C\n"
        "\n"
        "#### No milestone (1)\n"
        "- #30 Later\n"
    )


def test_gh_fetch_calls_gh_for_this_repo_and_stops_at_the_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    reply = {"n": 2}

    def fake_run(cmd: list[str], **_: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, json.dumps([{"number": 1}] * reply["n"]), "")

    monkeypatch.setattr(ds.subprocess, "run", fake_run)
    assert ds.gh_fetch("open_prs") == [{"number": 1}] * 2
    assert calls[0][:3] == ["gh", "pr", "list"]
    assert calls[0][-2:] == ["-R", ds.REPO]
    reply["n"] = ds.LIMIT
    with pytest.raises(SystemExit, match="raise LIMIT"):
        ds.gh_fetch("merged")


def test_a_mode_is_required() -> None:
    with pytest.raises(SystemExit):
        ds.main([], fetch=lambda kind: [])
