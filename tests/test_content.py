import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from markdown_it import MarkdownIt
from mdit_py_plugins.anchors import anchors_plugin

from app.config import settings
from app.content import Lesson, Option, Source, load_lessons, load_sources, validate
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures" / "content"


@pytest.fixture
def lessons() -> dict[str, Lesson]:
    return load_lessons(FIXTURES)


@pytest.fixture
def sources() -> dict[str, Source]:
    return load_sources(FIXTURES / "sources.yaml")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "content_root", str(FIXTURES))
    with TestClient(app) as c:
        yield c


def test_loader_fields(lessons: dict[str, Lesson]) -> None:
    lesson = lessons["fx-demo"]
    assert (lesson.track, lesson.title, lesson.minutes) == ("fastapi", "Demo lesson", 8)
    assert lesson.pins == {"fastapi": "0.143.0"}
    assert lesson.sources == ["fx-source"]
    assert [s.id for s in lesson.sections] == [
        "intro",
        "using-depends",
        "second-section",
        "see-the-docs-now",
    ]
    assert len(lesson.warmup) == 1
    assert [q.type for q in lesson.quiz] == ["single", "order", "blank"]
    assert len(lesson.deeper[0].rubric) == 3
    assert lesson.task_kind == "pytest"
    assert "<h1" in lesson.task_readme_html
    assert lesson.has_trace is False


def test_fenced_heading_is_not_a_section(lessons: dict[str, Lesson]) -> None:
    assert "not-a-heading" not in [s.id for s in lessons["fx-demo"].sections]


def test_section_ids_match_rendered_anchors(lessons: dict[str, Lesson]) -> None:
    md = MarkdownIt("js-default").use(anchors_plugin, max_level=3)
    for section in lessons["fx-demo"].sections[1:]:
        assert f'id="{section.id}"' in section.html
        assert f'id="{section.id}"' in md.render(f"## {section.title}")
    assert "see-the-docs-now" in [s.id for s in lessons["fx-demo"].sections]  # heading with a link


def test_fixture_is_valid(lessons: dict[str, Lesson], sources: dict[str, Source]) -> None:
    assert validate(lessons, sources) == []


def test_real_content_is_valid() -> None:
    root = Path(__file__).parents[1] / "content"
    assert validate(load_lessons(root), load_sources(root / "sources.yaml")) == []


def test_validate_catches_each_problem(lessons: dict[str, Lesson]) -> None:
    lesson = lessons["fx-demo"].model_copy(deep=True)
    lesson.sources = ["nope", "bare"]
    lesson.quiz[0].source_section = "missing"
    lesson.quiz[0].options = [Option(text="a", feedback="f"), Option(text="b", feedback="f")]
    lesson.quiz[1].steps = ["only"]
    lesson.deeper[0].rubric = lesson.deeper[0].rubric[:2]
    bare = Source(id="bare", title="Bare", url="https://example.com")
    problems = "\n".join(validate({lesson.id: lesson}, {"bare": bare}))
    for expected in [
        "unknown source id 'nope'",
        "missing license or attribution",
        "unknown source_section 'missing'",
        "exactly one correct option",
        "at least 2 steps",
        "at least 3 criteria",
    ]:
        assert expected in problems


def test_validate_flags_blank_items(lessons: dict[str, Lesson]) -> None:
    lesson = lessons["fx-demo"].model_copy(deep=True)
    blank = lesson.quiz[0].model_copy(update={"id": "b1", "type": "blank", "answer": ""})
    broken = blank.model_copy(update={"id": "b2", "answer": "re:(unclosed"})
    fine = blank.model_copy(update={"id": "b3", "answer": "re:depends?"})
    lesson.quiz = [blank, broken, fine]
    problems = validate({lesson.id: lesson}, {})
    assert "fx-demo/b1: blank item has an empty answer" in problems
    assert "fx-demo/b2: answer regex does not compile" in problems
    assert not any("b3" in p for p in problems)


def test_lesson_page(client: TestClient) -> None:
    r = client.get("/lessons/fx-demo")
    assert r.status_code == 200
    assert 'id="using-depends"' in r.text and 'id="second-section"' in r.text
    assert "Fixture source" in r.text and "https://example.com/fx" in r.text
    assert "MIT" in r.text and "Adapted from the Fixture docs" in r.text
    assert 'id="intro"' in r.text
    assert "<details>" in r.text  # warm-up


def test_unknown_lesson_is_404(client: TestClient) -> None:
    assert client.get("/lessons/nope").status_code == 404


def test_home_lists_fixture_and_empty_tracks(client: TestClient) -> None:
    text = client.get("/").text
    assert "Demo lesson" in text and "8 min" in text
    assert "No lessons yet" in text
    assert "GitHub for the Claude Code era" in text


def test_api_lessons(client: TestClient) -> None:
    assert client.get("/api/lessons").json() == [
        {"id": "fx-demo", "track": "fastapi", "title": "Demo lesson", "minutes": 8}
    ]


def _copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "content"
    shutil.copytree(FIXTURES, root)
    return root


def test_frontmatter_id_must_match_folder(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    (root / "fastapi" / "fx-demo").rename(root / "fastapi" / "other")
    with pytest.raises(ValueError, match="!= folder"):
        load_lessons(root)


def test_duplicate_lesson_id_is_rejected(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    shutil.copytree(root / "fastapi" / "fx-demo", root / "github" / "fx-demo")
    with pytest.raises(ValueError, match="duplicate lesson id"):
        load_lessons(root)


def test_lesson_id_pattern_and_frontmatter_required(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    md = root / "fastapi" / "fx-demo" / "lesson.md"
    text = md.read_text()
    md.write_text(text.replace("id: fx-demo", "id: Fx_Demo"))
    (root / "fastapi" / "Fx_Demo").mkdir()
    md.rename(root / "fastapi" / "Fx_Demo" / "lesson.md")
    with pytest.raises(ValueError, match="pattern"):
        load_lessons(root)
    (root / "fastapi" / "Fx_Demo" / "lesson.md").write_text("no frontmatter")
    with pytest.raises(ValueError, match="frontmatter"):
        load_lessons(root)
