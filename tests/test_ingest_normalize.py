"""Unit tests for app/ingest/normalize.py (small fixtures, no network)."""

from pathlib import Path

import pytest

from app.ingest.normalize import (
    normalize,
    normalize_fastapi,
    normalize_github,
    normalize_pydantic_ai,
    plain_alerts,
    strip_html,
)

FIXTURES = Path(__file__).parent / "fixtures" / "ingest"
KINDS = {
    "fastapi_raw": "fastapi_cached.md",
    "pydantic_ai_md": "pydantic_served.md",
    "github_article": "github_article.md",
}


def _read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_fastapi_keeps_anchors_and_code_and_drops_html() -> None:
    out = normalize_fastapi(_read("fastapi_cached.md"))
    assert "## First Steps <!-- anchor: first-steps -->" in out
    assert "### Import `Depends` <!-- anchor: import-depends -->" in out
    assert "**Dependency Injection**" in out and "<dfn" not in out and "<img" not in out
    assert "    # a comment that is not a heading" in out  # fenced code is untouched
    assert "**Python 3.10+**" in out  # a tab label stays a plain line


def test_fastapi_alerts_become_plain_labelled_blockquotes() -> None:
    out = normalize_fastapi(_read("fastapi_cached.md"))
    assert "[!NOTE]" not in out and "[!TIP]" not in out
    assert "> **Note**\n> FastAPI added support for `Annotated`" in out
    assert "> **Tip**\n> **Handy**\n> You can reuse" in out


@pytest.mark.parametrize("raw", ["{* ../../docs_src/x/y.py ln[1:2] *}", "{!../../docs_src/x.py!}"])
def test_fastapi_rejects_unresolved_includes(raw: str) -> None:
    with pytest.raises(ValueError, match="fetch_docs"):
        normalize_fastapi(f"# T\n\n{raw}\n")


@pytest.mark.parametrize("raw", ["/// tip | Title", "///", "//// tab | Python"])
def test_fastapi_rejects_raw_blocks(raw: str) -> None:
    with pytest.raises(ValueError, match="fetch_docs"):
        normalize_fastapi(f"# T\n\n{raw}\n")


def test_fastapi_raw_syntax_inside_a_fence_is_fine() -> None:
    text = "# T\n\n```text\n/// tip\n{* path *}\n```\n"
    assert "/// tip" in normalize_fastapi(text)


def test_pydantic_strips_the_agent_preamble_as_untrusted() -> None:
    out = normalize_pydantic_ai(_read("pydantic_served.md"))
    assert out.startswith("# Installation\n")
    for injected in ("Documentation Index", "Querying This Documentation", "query parameters"):
        assert injected not in out


def test_pydantic_admonitions_tabs_stubs_and_snippets() -> None:
    out = normalize_pydantic_ai(_read("pydantic_served.md"))
    assert "!!!" not in out and "===" not in out and ":::" not in out
    assert "**Note: Heads up**\n\nRequires Python 3.11+." in out
    assert '```python\n# a comment inside an indented fence\nprint("hi")\n```' in out  # dedented
    assert "**Python**\n\nUse the class directly." in out
    assert "**CLI**\n\nRun `clai` instead." in out
    assert "_(API reference for pydantic_ai.agent.Agent omitted)_" in out
    assert "show_source" not in out  # the stub's option lines go with it
    assert "_(code snippet omitted)_" in out and "hello.py" not in out


def test_pydantic_keeps_ids_links_and_cleans_noise() -> None:
    out = normalize_pydantic_ai(_read("pydantic_served.md"))
    assert "## Defining an agent {#defining-an-agent}" in out
    assert "See `Agent` and the [guide](https://example.com/guide)." in out  # autoref -> text
    assert "tab-panel" not in out
    assert "**File: run_agent.py**\n```python\nfrom pydantic_ai import Agent" in out
    assert "requires=" not in out


def test_pydantic_needs_an_h1() -> None:
    with pytest.raises(ValueError, match="H1"):
        normalize_pydantic_ai("just text\n")


def test_github_strips_tags_but_keeps_links_and_code() -> None:
    out = normalize_github(_read("github_article.md"))
    assert "[enforce workflows](https://docs.github.com/en/repositories/x)." in out
    for gone in ("<picture", "<img", "<div class", "<br>\n", "hidden comment", "[!NOTE]"):
        assert gone not in out
    assert "Use `git checkout <branch>` and the inline `<br>` tag stays as code." in out
    assert "# <div>not html</div>" in out  # inside a fence
    assert "Wrapped text stays." in out
    assert "> **Note**\n> Rulesets are available" in out


def test_strip_html_leaves_non_html_angle_brackets() -> None:
    assert strip_html("run <branch> and a < b > c") == "run <branch> and a < b > c"
    assert strip_html("x<br/>y <b>bold</b>") == "xy bold"


def test_plain_alerts_only_outside_fences() -> None:
    text = "> [!WARNING]\n> careful\n\n```md\n> [!WARNING]\n```\n"
    out = plain_alerts(text)
    assert out.startswith("> **Warning**\n> careful")
    assert "```md\n> [!WARNING]\n```" in out


@pytest.mark.parametrize(("kind", "name"), KINDS.items())
def test_normalising_twice_changes_nothing(kind: str, name: str) -> None:
    once = normalize(kind, _read(name))
    assert normalize(kind, once) == once
    assert once.endswith("\n") and "\n\n\n" not in once


def test_unknown_kind_is_an_error() -> None:
    with pytest.raises(ValueError, match="unknown source kind"):
        normalize("nope", "# T\n")


def test_blank_lines_inside_code_are_kept_and_elsewhere_collapsed() -> None:
    text = "# T\n\n\n\nText.\n\n\n```python\na = 1\n\n\n\nb = 2\n```\n\n\n"
    assert normalize_github(text) == "# T\n\nText.\n\n```python\na = 1\n\n\n\nb = 2\n```\n"


def test_html_comments_go_even_across_lines_but_anchor_ids_and_code_stay() -> None:
    text = (
        "## Title <!-- anchor: title -->\n\nBefore <!-- one\nline comment --> after.\n\n"
        "Write `<!-- not a comment -->` in HTML.\n\n```html\n<!-- code -->\n```\n"
    )
    out = strip_html(text)
    assert "## Title <!-- anchor: title -->" in out
    assert "Before  after." in out and "one" not in out
    assert "Write `<!-- not a comment -->` in HTML." in out and "<!-- code -->" in out


def test_comments_across_blank_lines_and_script_style_tags_go() -> None:
    text = 'Before <!-- a\n\nb --> after.\n\n<style>x</style><iframe src="u"></iframe>Text.\n'
    out = strip_html(text)
    assert out.startswith("Before  after.") and "<style" not in out and "<iframe" not in out
    assert out.rstrip().endswith("xText.")  # the tags go, the text between them stays


def test_raw_pages_get_the_same_clean_up_as_github_pages() -> None:
    text = "# Intro\n\n> [!NOTE]\n> Hi <b>there</b>.\n\n```yaml\n# not a heading\n```\n"
    assert (
        normalize("raw", text)
        == "# Intro\n\n> **Note**\n> Hi there.\n\n```yaml\n# not a heading\n```\n"
    )
