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
