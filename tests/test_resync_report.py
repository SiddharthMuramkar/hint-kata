"""Unit tests for scripts/resync_report.py (small fixtures, no network)."""

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
import yaml

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "resync_report.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("resync_report", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rr = _load()


def _manifest(**shas: str | None) -> dict[str, list[dict[str, str | None]]]:
    return {"sources": [{"id": i, "title": f"Title {i}", "sha256": s} for i, s in shas.items()]}


def _lesson(root: Path, track: str, name: str, sources: list[str] | None) -> None:
    folder = root / track / name
    folder.mkdir(parents=True)
    front = {"id": name, "title": name, **({"sources": sources} if sources is not None else {})}
    (folder / "lesson.md").write_text(f"---\n{yaml.safe_dump(front)}---\nBody.\n")


def test_changed_ids_compares_sha256() -> None:
    old = _manifest(a="1" * 64, b="2" * 64, c=None, gone="3" * 64)
    new = _manifest(a="1" * 64, b="9" * 64, c="4" * 64, fresh="5" * 64, empty=None)
    assert rr.changed_ids(old, new) == ["b", "c", "fresh"]  # removed ids are not "changed"


def test_changed_ids_with_no_old_manifest_is_everything() -> None:
    assert rr.changed_ids({}, _manifest(a="1", b="2")) == ["a", "b"]


def test_failed_ids_reads_only_failed_lines() -> None:
    log = (
        "ok      src-one                 12 B  abcdef012345\n"
        "FAILED  src-two                 OSError: HTTP Error 503\n"
        "changed src-three               9 B  fedcba543210\n"
        "FAILED  src-four                ValueError: no H1 found\n"
        "FAILED\n"
    )
    assert rr.failed_ids(log) == ["src-two", "src-four"]
    assert rr.failed_ids("") == []


def test_link_only_entries_are_never_changed_or_failed() -> None:
    """A `kind: link` entry has no sha256 ever, and fetch_docs prints it as `link`, not `FAILED`."""
    link = {"id": "l", "kind": "link", "title": "T"}
    page = {"id": "p", "title": "P", "sha256": "1" * 64}
    assert rr.changed_ids({"sources": [page]}, {"sources": [link, page]}) == []
    log = "link    l                       not fetched (link only)\nFAILED  p   OSError: x\n"
    assert rr.failed_ids(log) == ["p"]


def test_lesson_sources_and_stale_lessons(tmp_path: Path) -> None:
    _lesson(tmp_path, "fastapi", "fa1", ["a", "b"])
    _lesson(tmp_path, "github", "gh1", ["c"])
    _lesson(tmp_path, "github", "gh2", None)
    (tmp_path / "github" / "notes.md").write_text("not a lesson")
    lessons = rr.lesson_sources(tmp_path)
    assert lessons == {"fa1": ["a", "b"], "gh1": ["c"], "gh2": []}
    assert rr.stale_lessons(lessons, ["b", "c", "z"]) == {"fa1": ["b"], "gh1": ["c"]}
    assert rr.stale_lessons(lessons, []) == {}


def test_render_lists_changes_lessons_and_failures() -> None:
    old = _manifest(a="aaaaaaaa11", b="bbbbbbbb22", c="cccccccc33")
    new = _manifest(a="aaaaaaaa11", b="dddddddd44", c="cccccccc33")
    lessons = {"fa1": ["a", "b"], "gh1": ["a"]}
    report = rr.render(old, new, ["c"], lessons)
    assert "1 of 3 source pages changed" in report
    assert "- `b`: Title b (`bbbbbbbb` to `dddddddd`)" in report
    assert "### Lessons to re-check (1)" in report
    assert "- `fa1` cites `b`" in report and "gh1" not in report
    assert "### Failed to fetch (1)\n" in report and "- `c`" in report
    assert "GITHUB_TOKEN" in report and "Approve workflows to run" in report


def test_render_when_nothing_changed() -> None:
    same = _manifest(a="1" * 64)
    report = rr.render(same, same, [], {"fa1": ["a"]})
    assert "0 of 1 source pages changed" in report
    assert "###" in report and "Changed sources" not in report
    assert "Lessons to re-check" not in report and "Failed to fetch" not in report


def test_render_handles_a_new_source_without_hash() -> None:
    report = rr.render({}, _manifest(a=None, b="1" * 8), [], {})
    assert "(`none` to `none`)" not in report  # a is unchanged (None == missing)
    assert "- `b`: Title b (`none` to `11111111`)" in report


def _git(repo: Path, *args: str) -> None:
    cmd = [
        "git",
        "-c",
        "user.name=t",
        "-c",
        "user.email=t@example.com",
        "-c",
        "commit.gpgsign=false",
    ]
    subprocess.run([*cmd, *args], cwd=repo, check=True, capture_output=True)


def test_main_reads_old_manifest_from_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _git(tmp_path, "init", "-q")
    _lesson(tmp_path / "content", "fastapi", "fa1", ["a"])
    manifest = tmp_path / "content" / "sources.yaml"
    manifest.write_text(yaml.safe_dump(_manifest(a="1" * 64, b="2" * 64)))
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-q", "-m", "old")
    manifest.write_text(yaml.safe_dump(_manifest(a="9" * 64, b="2" * 64)))
    (tmp_path / "fetch.log").write_text("FAILED  b   OSError: boom\n")
    monkeypatch.chdir(tmp_path)

    assert rr.main(["--fetch-log", "fetch.log"]) == 0
    out = capsys.readouterr().out
    assert "- `a`: Title a" in out and "- `fa1` cites `a`" in out and "- `b`" in out

    assert rr.main(["--ids-only"]) == 0
    assert capsys.readouterr().out == "a\n"


def test_main_exits_0_even_without_a_git_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "sources.yaml").write_text(yaml.safe_dump(_manifest(a="1" * 64)))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))  # not inside a repo

    assert rr.main([]) == 0
    captured = capsys.readouterr()
    assert "1 of 1 source pages changed" in captured.out
    assert "warning: no manifest at HEAD" in captured.err
