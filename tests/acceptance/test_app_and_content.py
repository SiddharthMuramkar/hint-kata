"""SPEC section 23 rows: App runs, Content loads, Warm-up."""

import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
from markupsafe import escape

from app.content import Lesson, load_lessons, load_sources, validate

from .conftest import ALL, LESSONS, ROOT, lessons_with


def test_app_runs(client: TestClient) -> None:
    home = client.get("/")
    assert home.status_code == 200
    assert 'name="color-scheme" content="dark"' in home.text  # dark theme
    assert "not affiliated" in home.text
    licenses = client.get("/licenses")
    assert licenses.status_code == 200 and "CC BY 4.0" in licenses.text and "MIT" in licenses.text
    assert client.get("/healthz").json() == {"ok": True}


def test_no_page_returns_a_5xx(client: TestClient) -> None:
    paths = ["/", "/today", "/licenses", "/api/lessons", "/api/progress", "/api/review"]
    paths += [f"/lessons/{lid}" for lid in LESSONS]
    assert all(client.get(p).status_code < 500 for p in paths)


def test_home_lists_every_lesson(client: TestClient) -> None:
    text = client.get("/").text
    assert all(f'href="/lessons/{lid}"' in text for lid in LESSONS)


@pytest.mark.parametrize("lesson", ALL)
def test_lesson_renders_with_anchors_and_attribution(client: TestClient, lesson: Lesson) -> None:
    page = client.get(f"/lessons/{lesson.id}")
    assert page.status_code == 200
    assert lesson.sections
    for section in lesson.sections:
        assert f'id="{section.id}"' in page.text
    sources = load_sources(ROOT / "content" / "sources.yaml")
    assert lesson.sources
    for sid in lesson.sources:
        s = sources[sid]
        assert s.license and s.attribution  # not just in the file: shown on the page
        for text in (s.url, s.license, s.attribution):
            assert str(escape(text)) in page.text


def test_content_validates() -> None:
    root = ROOT / "content"
    assert validate(load_lessons(root), load_sources(root / "sources.yaml")) == []


def test_fetch_docs_check_passes_offline() -> None:
    if not (ROOT / ".cache" / "docs").is_dir():
        pytest.skip("no .cache/docs here (CI never fetches); run scripts/fetch_docs.py first")
    proc = subprocess.run(
        [sys.executable, "scripts/fetch_docs.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("lesson", lessons_with("warmup"))
def test_warmup_is_shown_before_the_reading(client: TestClient, lesson: Lesson) -> None:
    """Warm-ups are plain `<details>` on the page (nothing is stored, nothing is scored)."""
    text = client.get(f"/lessons/{lesson.id}").text
    assert text.index('class="card warmup"') < text.index('class="markdown-body"')
    for w in lesson.warmup:
        assert str(escape(w.prompt)) in text
