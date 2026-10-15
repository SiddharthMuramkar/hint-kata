import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "app/static/css/app.css").read_text()
HOME = (ROOT / "app/templates/home.html").read_text()

TOKENS = {
    "#212830",  # canvas
    "#262c36",  # raised surface
    "#d1d7e0",  # text
    "#9198a1",  # muted text
    "#478be6",  # blue
    "#3d444d",  # border
    "#d29922",  # learning
    "#3fb950",  # mastered
    "#f85149",  # wrong
}

JS_SELECTORS = [
    ".badge",
    ".badge.notstarted",
    ".badge.learning",
    ".badge.mastered",
    ".quiz-opt",
    ".quiz-opt.sel",
    ".quiz-msg",
    ".quiz-msg.ok",
    ".quiz-msg.bad",
    ".review-card",
    "#quiz",
    "#tutor",
    "#check-output",
]


def test_only_token_hex_colors() -> None:
    used = {m.group(0).lower() for m in re.finditer(r"#[0-9a-fA-F]{6}\b", CSS)}
    assert used <= TOKENS
    assert TOKENS <= used  # every token is defined


def test_js_selectors_present() -> None:
    for sel in JS_SELECTORS:
        assert sel in CSS, sel


def test_no_markdown_body_rules() -> None:
    assert ".markdown-body" not in CSS


def test_track_hooks() -> None:
    assert "track-card" in HOME
    assert "track-lessons" in HOME
    assert "rgba(209, 215, 224, 0.06)" in CSS  # row hover overlay
    assert "min-height: 44px" in CSS
