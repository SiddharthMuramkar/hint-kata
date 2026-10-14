"""Watch-it-run traces: curated, step-indexed replays (docs/SPEC.md section 8)."""

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.config import settings


class Citation(BaseModel):
    url: str
    title: str


class Annotation(BaseModel):
    why: str
    concept_tags: list[str] = []
    citations: list[Citation] = []


class Checkpoint(BaseModel):
    type: Literal["predict_next"]
    prompt: str
    options: list[str]
    answer: int
    explanation: str


class Step(BaseModel):
    idx: int
    kind: str
    actor: str
    title: str
    summary: str
    payload_excerpt: str = ""
    metrics: dict[str, int | float | str] = {}
    annotation: Annotation | None = None
    checkpoint: Checkpoint | None = None


class Trace(BaseModel):
    id: str
    kind: Literal["pydantic_ai_run", "github_pr"]
    title: str
    objectives: list[str]
    source: dict[str, object]
    steps: list[Step]
    takeaways: list[str]


def load_trace(lesson_id: str, content_root: Path | None = None) -> Trace | None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", lesson_id):
        return None
    root = content_root or Path(settings.content_root)
    for path in sorted(root.glob(f"*/{lesson_id}/trace.json")):
        return Trace.model_validate_json(path.read_text())
    return None


def public_view(trace: Trace) -> dict[str, object]:
    """The trace as sent to the browser: checkpoint answers and explanations removed."""
    return trace.model_dump(
        exclude={"steps": {"__all__": {"checkpoint": {"answer", "explanation"}}}}
    )


def grade(trace: Trace, step_idx: int, choice: int) -> tuple[bool, str]:
    """Check a learner's choice at a checkpoint. Raises KeyError if the step has none."""
    for step in trace.steps:
        if step.idx == step_idx and step.checkpoint:
            return choice == step.checkpoint.answer, step.checkpoint.explanation
    raise KeyError(step_idx)
