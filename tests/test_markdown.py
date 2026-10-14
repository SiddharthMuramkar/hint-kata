from app.markdown import render_markdown


def test_script_and_javascript_links_never_survive() -> None:
    out = str(render_markdown("<script>alert(1)</script> [x](javascript:alert(1))"))
    assert "<script>" not in out
    # The link is refused and left as escaped text, so there is no live href.
    assert 'href="javascript:' not in out.lower()
    assert "<a " not in out


def test_fenced_code_is_highlighted() -> None:
    out = str(render_markdown("```python\nprint('hi')\n```"))
    assert '<pre class="highlight"><code class="language-python">' in out


def test_heading_gets_anchor_id() -> None:
    assert 'id="hello-world"' in str(render_markdown("## Hello world"))


def test_alert_renders() -> None:
    assert "markdown-alert" in str(render_markdown("> [!NOTE]\n> Careful."))
