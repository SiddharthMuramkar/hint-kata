"""Unit tests for scripts/fetch_docs.py (no network)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fetch_docs.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fetch_docs", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fd = _load()

PREAMBLE_PAGE = """> ## Documentation Index
> Fetch the complete documentation index at: https://example.com/llms.txt

## Querying This Documentation

Include these query parameters when fetching any page.

---

# Dependencies

Intro.

## Querying This Documentation

Another injected block.

### Sub heading of the injected block

## Real Section

Body.
"""


def test_strip_pydantic_preamble_and_agent_sections() -> None:
    out = fd.strip_pydantic(PREAMBLE_PAGE)
    assert out.startswith("# Dependencies\n")
    assert "Documentation Index" not in out
    assert "Querying" not in out
    assert "Sub heading" not in out
    assert "## Real Section\n\nBody.\n" in out


def test_strip_pydantic_requires_h1() -> None:
    with pytest.raises(ValueError):
        fd.strip_pydantic("no heading here\n")


SOURCE = "\n".join(f"line{i}" for i in range(1, 11))


def test_select_lines_ranges() -> None:
    assert fd.select_lines(SOURCE, "2:3") == "line2\nline3"
    assert fd.select_lines(SOURCE, "1,3:4") == "line1\n# ...\nline3\nline4"
    assert fd.select_lines(SOURCE, "1:2,3") == "line1\nline2\nline3"
    assert fd.select_lines(SOURCE, "0") == SOURCE


def test_resolve_includes_star_and_bang() -> None:
    asked: list[str] = []

    def read(path: str) -> str:
        asked.append(path)
        return SOURCE

    star = '{* ../../docs_src/x/a.py ln[2:3] hl[1] title["a.py"] *}'
    text = f"before\n{star}\n{{!> ../../docs_src/x/b.py!}}\nafter"
    out = fd.resolve_includes(text, read)
    assert asked == ["docs_src/x/a.py", "docs_src/x/b.py"]
    assert "```python\nline2\nline3\n```" in out
    assert out.count("```python") == 2
    assert "line10" in out  # the {! include has no ln, so the whole file
    assert out.startswith("before\n") and out.endswith("after")
    assert "{*" not in out and "{!" not in out


def test_repo_path_rejects_escape() -> None:
    assert fd.repo_path("../../docs_src/a.py") == "docs_src/a.py"
    with pytest.raises(ValueError):
        fd.repo_path("../../../../etc/passwd")


def test_admonitions_and_tabs() -> None:
    text = """/// tip | Handy

Use `Depends`.
///

/// danger
Careful.
///

/// details | More
Hidden.
///

//// tab | Python 3.10+

body
////
"""
    out = fd.convert_blocks(text)
    assert "> [!TIP]\n> **Handy**\n> \n" not in out  # no stray blank edge lines
    assert "> [!TIP]\n> **Handy**\n> Use `Depends`." in out
    assert "> [!CAUTION]\n> Careful." in out
    assert "> [!NOTE]\n> **More**\n> Hidden." in out
    assert "**Python 3.10+**\n\nbody" in out
    assert "////" not in out and "///" not in out


def test_unterminated_admonition_fails() -> None:
    with pytest.raises(ValueError):
        fd.convert_blocks("/// note\nnever closed\n")


def test_anchor_comment() -> None:
    out = fd.convert_anchors("## Request Body { #request-body }\n# Plain\ntext { #not-a-heading }")
    assert out == "## Request Body <!-- anchor: request-body -->\n# Plain\ntext { #not-a-heading }"


def test_clean_github_links_and_svg() -> None:
    text = (
        'See [PRs](/en/pull-requests) <svg class="x">\n<path d="M0"/></svg> done\n[ok](https://a.b)'
    )
    out = fd.clean_github(text)
    assert "](https://docs.github.com/en/pull-requests)" in out
    assert "<svg" not in out and "<path" not in out
    assert "[ok](https://a.b)" in out
    img = fd.clean_github("![x](/assets/images/a.png)")
    assert img == "![x](https://docs.github.com/assets/images/a.png)\n"


def _manifest(tmp_path: Path, sha: str = "") -> Path:
    entry = {"id": "s1", "track": "github", "kind": "github_article", "sha256": sha}
    path = tmp_path / "sources.json"
    path.write_text(json.dumps({"sources": [{**entry, "fetch_url": "https://x/y"}]}))
    return path


def test_update_then_check_roundtrip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(fd, "fetch", lambda url: "hello [a](/en/x)\n")
    manifest, cache = _manifest(tmp_path), tmp_path / "cache"
    assert fd.main(["--manifest", str(manifest), "--cache", str(cache), "--update"]) == 0

    entry = json.loads(manifest.read_text())["sources"][0]
    cached = cache / "github" / "s1.md"
    assert cached.read_text() == "hello [a](https://docs.github.com/en/x)\n"
    assert entry["sha256"] == fd.sha256(cached.read_text())
    assert entry["fetched_at"].endswith("Z")

    assert fd.main(["--manifest", str(manifest), "--cache", str(cache), "--check"]) == 0
    assert "ok" in capsys.readouterr().out


def test_update_skips_a_failed_page_and_exits_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fake(url: str) -> str:
        if url.endswith("/bad"):
            raise OSError("HTTP Error 503\nunavailable")
        return "ok text\n"

    monkeypatch.setattr(fd, "fetch", fake)
    base = {"track": "github", "kind": "github_article", "sha256": "old", "fetched_at": "then"}
    entries = [
        {**base, "id": "bad", "fetch_url": "https://x/bad"},
        {**base, "id": "good", "fetch_url": "https://x/good"},
    ]
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"sources": entries}))
    args = ["--manifest", str(manifest), "--cache", str(tmp_path / "cache"), "--update"]
    assert fd.main(args) == 1

    bad, good = json.loads(manifest.read_text())["sources"]
    assert (bad["sha256"], bad["fetched_at"]) == ("old", "then")  # left as it was
    assert good["sha256"] == fd.sha256("ok text\n") and good["fetched_at"] != "then"
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split()[:2] == ["FAILED", "bad"] and "OSError" in lines[0]
    assert len(lines) == 2  # the error text stays on one line


def test_check_detects_mismatch_and_missing(tmp_path: Path) -> None:
    cache = tmp_path / "cache"
    manifest = _manifest(tmp_path, sha=fd.sha256("expected"))
    args = ["--manifest", str(manifest), "--cache", str(cache), "--check"]
    assert fd.main(args) == 1  # cached file missing

    (cache / "github").mkdir(parents=True)
    (cache / "github" / "s1.md").write_text("something else")
    assert fd.main(args) == 1  # hash mismatch

    (cache / "github" / "s1.md").write_text("expected")
    assert fd.main(args) == 0


def test_check_fails_when_no_entry_has_sha(tmp_path: Path) -> None:
    manifest = _manifest(tmp_path)
    assert fd.main(["--manifest", str(manifest), "--cache", str(tmp_path / "c"), "--check"]) == 1


def test_fastapi_end_to_end_with_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    inc = "{* ../../docs_src/d/t.py ln[%s] *}"
    page = f"# Title {{ #title }}\n\n{inc % '1:2'}\n{inc % '3'}\n"

    def fake(url: str) -> str:
        calls.append(url)
        return page if url.endswith("index.md") else "a = 1\nb = 2\nc = 3\n"

    monkeypatch.setattr(fd, "fetch", fake)
    entry = {"id": "f", "track": "fastapi", "kind": "fastapi_raw", "version": "9.9.9"}
    entry["fetch_url"] = "https://raw/index.md"
    out = fd.build(entry, tmp_path)
    assert out.startswith("# Title <!-- anchor: title -->")
    assert "```python\na = 1\nb = 2\n```" in out and "```python\nc = 3\n```" in out
    assert calls == ["https://raw/index.md", f"{fd.FASTAPI_RAW}/9.9.9/docs_src/d/t.py"]


def test_raw_kind_keeps_the_page_exactly_as_served(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    page = "> keep this\r\n\r\n# Title  \r\n\r\ntrailing space \n"
    monkeypatch.setattr(fd, "fetch", lambda url: page)
    entry = {"id": "r", "track": "github", "kind": "raw", "fetch_url": "https://x/y.md"}
    assert fd.build(entry, tmp_path) == page


def test_raw_with_crlf_survives_update_then_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fd, "fetch", lambda url: "line one\r\nline two\r\n")
    entry = {"id": "r", "track": "github", "kind": "raw", "fetch_url": "https://x/y.md"}
    manifest = tmp_path / "sources.json"
    manifest.write_text(json.dumps({"sources": [entry]}))
    args = ["--manifest", str(manifest), "--cache", str(tmp_path / "cache")]
    assert fd.main([*args, "--update"]) == 0
    assert fd.main([*args, "--check"]) == 0  # the check reads bytes, so CRLF cannot drift


def _link_manifest(tmp_path: Path) -> Path:
    link = {"id": "l", "track": "github", "kind": "link", "url": "https://x/docs/page"}
    page = {"id": "p", "track": "github", "kind": "raw", "fetch_url": "https://x/p.md"}
    path = tmp_path / "sources.json"
    path.write_text(json.dumps({"sources": [link, page]}))
    return path


def test_link_entries_are_never_fetched_or_updated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[str] = []

    def fake(url: str) -> str:
        asked.append(url)
        return "body\n"

    monkeypatch.setattr(fd, "fetch", fake)
    manifest, cache = _link_manifest(tmp_path), tmp_path / "cache"
    assert fd.main(["--manifest", str(manifest), "--cache", str(cache), "--update"]) == 0
    assert asked == ["https://x/p.md"]  # nothing was requested for the link
    link, page = json.loads(manifest.read_text())["sources"]
    assert "sha256" not in link and "fetched_at" not in link
    assert page["sha256"] == fd.sha256("body\n")
    assert not (cache / "github" / "l.md").exists()


def test_link_entry_is_never_failed_next_to_a_failing_page(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def boom(url: str) -> str:
        raise OSError("HTTP Error 503")

    monkeypatch.setattr(fd, "fetch", boom)
    manifest = _link_manifest(tmp_path)
    assert fd.main(["--manifest", str(manifest), "--cache", str(tmp_path / "c"), "--update"]) == 1
    lines = capsys.readouterr().out.splitlines()
    assert [ln.split()[:2] for ln in lines] == [["link", "l"], ["FAILED", "p"]]


def test_check_reports_link_entries_as_link_not_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(fd, "fetch", lambda url: "body\n")
    manifest, cache = _link_manifest(tmp_path), tmp_path / "cache"
    base = ["--manifest", str(manifest), "--cache", str(cache)]
    assert fd.main([*base, "--update"]) == 0
    capsys.readouterr()
    assert fd.main([*base, "--check"]) == 0
    out = capsys.readouterr().out
    assert "link     l" in out and "MISSING" not in out
    assert "1 ok, 0 failed, 1 link-only" in out
    assert fd.main([*base, "--check", "--only", "l"]) == 0  # only a link: nothing to hash


def test_build_refuses_a_link_entry(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        fd.build({"id": "l", "kind": "link", "url": "https://x"}, tmp_path)
