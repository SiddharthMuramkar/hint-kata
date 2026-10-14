"""Shared setup for the SPEC section 23 acceptance suite: the real content, a temp DB, no models."""

import json
import re
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic_ai import Agent, NativeOutput, models
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from app.agents import grader
from app.agents.grader import Grade, GraderDeps
from app.config import settings
from app.content import DeeperQuestion, Lesson, QuizItem, load_lessons
from app.main import app
from app.quiz import scramble
from app.routes.tutor import get_tutor
from app.store import SqliteStore, open_store

ROOT = Path(__file__).resolve().parents[2]
LESSONS = load_lessons(ROOT / "content")

TUTOR_REPLY = "See [§{first}] and [§bogus].\n\n```python\nx = 1\n```\n"


def lessons_with(attr: str) -> list[Any]:
    """Parametrize helper: the lessons that have the feature, so nothing is skipped."""
    return [pytest.param(x, id=x.id) for x in LESSONS.values() if getattr(x, attr)]


ALL = lessons_with("id")


def _first_section(info: AgentInfo) -> str:
    """The tutor's instructions list the sections as `[§id] Title`; cite the first one."""
    m = re.search(r"\[§([a-z0-9-]+)\]", info.instructions or "")
    assert m, "the tutor instructions carry no section ids"
    return m[1]


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """The app over the real content and a temp DB. Models are blocked; the tutor is faked."""
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    monkeypatch.setattr(settings, "content_root", str(ROOT / "content"))
    monkeypatch.setattr(settings, "hintkata_db_path", str(tmp_path / "t.db"))

    def reply(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(TUTOR_REPLY.format(first=_first_section(info)))])

    async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator[str]:
        yield TUTOR_REPLY.format(first=_first_section(info))

    fake = FunctionModel(reply, stream_function=stream)
    with TestClient(app) as c, get_tutor().override(model=fake):
        yield c


@pytest.fixture
def store(client: TestClient) -> Iterator[SqliteStore]:
    s = open_store(settings.hintkata_db_path)
    yield s
    s.close()


@pytest.fixture
def uid(store: SqliteStore) -> int:
    return store.ensure_user("owner")


def use_grader(
    monkeypatch: pytest.MonkeyPatch, q: DeeperQuestion, met: list[bool] | None = None
) -> list[int]:
    """Fake the grader: every sample returns `met` for the rubric (default all met).
    Returns a list that gets one entry per model call."""
    verdicts = met or [True] * len(q.rubric)
    calls: list[int] = []
    grade = Grade(
        criteria=[
            grader.CriterionResult(name=c.name, evidence="quote", reasoning="r", met=m)
            for c, m in zip(q.rubric, verdicts, strict=True)
        ],
        feedback="ok",
        hints=[f"hint {c.name}" for c, m in zip(q.rubric, verdicts, strict=True) if not m],
    )

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        calls.append(1)
        return ModelResponse(parts=[TextPart(grade.model_dump_json())])

    agent = Agent(
        FunctionModel(respond),
        deps_type=GraderDeps,
        output_type=NativeOutput(Grade),
        instructions=grader._instructions,
    )
    monkeypatch.setattr(grader, "make_grader", lambda model=None: agent)
    return calls


def post_quiz(
    client: TestClient,
    lesson: Lesson,
    item: QuizItem,
    answer: Any,
    try_no: int = 1,
    confidence: str = "thinkso",
) -> Any:
    body = {"answer": answer, "confidence": confidence, "try_no": try_no, "elapsed_ms": 20_000}
    return client.post(f"/api/quiz/{lesson.id}/{item.id}", json=body)


def singles(lesson: Lesson) -> list[QuizItem]:
    return [q for q in lesson.quiz if q.type == "single"]


def right(item: QuizItem) -> Any:
    """A correct answer for a single or order item."""
    if item.type == "single":
        return next(i for i, o in enumerate(item.options) if o.correct)
    shown = scramble(item)
    return [shown.index(i) for i in range(len(shown))]


def wrong(item: QuizItem) -> int:
    """A wrong option that has a misconception recorded."""
    return next(i for i, o in enumerate(item.options) if not o.correct and o.misconception)


def sse(body: str) -> dict[str, Any]:
    """Parse an SSE body into {event: data} (JSON when it parses, else the raw text)."""
    out: dict[str, Any] = {}
    for block in body.strip().split("\n\n"):
        fields = dict(line.split(": ", 1) for line in block.splitlines() if ": " in line)
        if "event" in fields:
            try:
                out[fields["event"]] = json.loads(fields["data"])
            except json.JSONDecodeError:
                out[fields["event"]] = fields["data"]
    return out
