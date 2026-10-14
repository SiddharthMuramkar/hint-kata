"""Lesson content: pydantic models, a loader for content/<track>/<lesson>/, and validate()."""

import re
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from app.markdown import render_markdown


class Source(BaseModel):
    id: str
    title: str
    url: str
    track: str = ""
    version: str = ""
    license: str = ""
    attribution: str = ""
    fetched_at: str = ""


class Section(BaseModel):
    id: str
    title: str
    html: str
    level: int = 2


class WarmupItem(BaseModel):
    id: str
    prompt: str
    note: str = ""


class Option(BaseModel):
    text: str
    correct: bool = False
    misconception: str = ""
    feedback: str


class QuizItem(BaseModel):
    id: str
    type: Literal["single", "order", "blank"]
    concept: str
    source_section: str
    prompt: str
    options: list[Option] = []
    steps: list[str] = []
    answer: str = ""
    explanation: str = ""


class Criterion(BaseModel):
    name: str
    explanation: str
    pass_anchor: str
    fail_anchor: str


class DeeperQuestion(BaseModel):
    id: str
    prompt: str
    rubric: list[Criterion]
    model_answer: str
    hints: list[str] = []


class Lesson(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    track: str
    title: str
    minutes: int
    pins: dict[str, str] = {}
    sources: list[str] = []
    sections: list[Section] = []
    warmup: list[WarmupItem] = []
    quiz: list[QuizItem] = []
    deeper: list[DeeperQuestion] = []
    task_kind: Literal["pytest", "gh"] | None = None
    task_readme_html: str = ""
    has_trace: bool = False
    dir: Path


def _yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None


def _split_sections(body: str, title: str) -> list[Section]:
    """Split on `## ` headings, ignoring any inside code fences. Text before the first one
    becomes an intro section."""
    chunks: list[tuple[str, list[str]]] = [("", [])]
    fence = ""
    for line in body.splitlines():
        if m := re.match(r"(`{3,}|~{3,})", line):
            fence = "" if fence and line.startswith(fence) else fence or m.group(1)
        if not fence and line.startswith("## "):
            chunks.append((line[3:].strip(), [line]))
        else:
            chunks[-1][1].append(line)
    out = []
    for heading, lines in chunks:
        text = "\n".join(lines).strip()
        if not (heading or text):
            continue
        html = str(render_markdown(text))
        # Read the id the anchors plugin gave the heading, so the two can never disagree.
        m = re.search(r'<h2 id="([^"]+)"', html) if heading else None
        out.append(Section(id=m.group(1) if m else "intro", title=heading or title, html=html))
    return out


def _load_lesson(md_path: Path) -> Lesson:
    d = md_path.parent
    raw = md_path.read_text(encoding="utf-8")
    if not raw.startswith("---"):
        raise ValueError(f"{md_path}: lesson.md must start with YAML frontmatter ('---')")
    _, front, body = raw.split("---", 2)
    meta = yaml.safe_load(front)
    if meta.get("id") != d.name:
        raise ValueError(f"{md_path}: frontmatter id {meta.get('id')!r} != folder {d.name!r}")
    meta["pins"] = {str(k): str(v) for k, v in (meta.get("pins") or {}).items()}
    readme = d / "task" / "README.md"
    task_kind = "pytest" if (d / "task" / "tests").is_dir() else None
    if (d / "task" / "check.yaml").exists():
        task_kind = "gh"
    return Lesson(
        **meta,
        sections=_split_sections(body, meta["title"]),
        warmup=[WarmupItem(**i) for i in (_yaml(d / "warmup.yaml") or {}).get("items", [])],
        quiz=[QuizItem(**i) for i in (_yaml(d / "quiz.yaml") or {}).get("items", [])],
        deeper=[DeeperQuestion(**q) for q in (_yaml(d / "deeper.yaml") or {}).get("questions", [])],
        task_kind=task_kind,
        task_readme_html=(
            str(render_markdown(readme.read_text(encoding="utf-8"))) if readme.exists() else ""
        ),
        has_trace=(d / "trace.json").exists(),
        dir=d,
    )


def load_lessons(root: Path = Path("content")) -> dict[str, Lesson]:
    out: dict[str, Lesson] = {}
    for p in sorted(root.glob("*/*/lesson.md")):
        lesson = _load_lesson(p)
        if lesson.id in out:
            raise ValueError(f"duplicate lesson id {lesson.id!r} ({p})")
        out[lesson.id] = lesson
    return out


def load_sources(path: Path) -> dict[str, Source]:
    data = _yaml(path) or {}
    return {s["id"]: Source(**s) for s in data.get("sources", [])}


def validate(lessons: dict[str, Lesson], sources: dict[str, Source]) -> list[str]:
    problems: list[str] = []
    for lesson in lessons.values():
        where = lesson.id
        for sid in lesson.sources:
            if sid not in sources:
                problems.append(f"{where}: unknown source id {sid!r}")
            elif not (sources[sid].license and sources[sid].attribution):
                problems.append(f"{where}: source {sid!r} is missing license or attribution")
        section_ids = {s.id for s in lesson.sections}
        for item in lesson.quiz:
            if item.source_section not in section_ids:
                problems.append(
                    f"{where}/{item.id}: unknown source_section {item.source_section!r}"
                )
            if item.type == "single" and sum(o.correct for o in item.options) != 1:
                problems.append(
                    f"{where}/{item.id}: single-choice needs exactly one correct option"
                )
            if item.type == "order" and len(item.steps) < 2:
                problems.append(f"{where}/{item.id}: order item needs at least 2 steps")
        for q in lesson.deeper:
            if len(q.rubric) < 3:
                problems.append(f"{where}/{q.id}: deeper question needs at least 3 criteria")
    return problems
