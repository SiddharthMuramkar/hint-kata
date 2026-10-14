"""Mastery rule (SPEC section 9): learning -> mastered, recomputed from stored evidence."""

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal

from app.config import settings
from app.content import Lesson
from app.quiz import score
from app.store import Store

State = Literal["notstarted", "learning", "mastered"]


@dataclass
class MasteryConfig:
    quiz_threshold: float = 0.8
    recalls_required: int = 2


def _config() -> MasteryConfig:
    return MasteryConfig(settings.mastery_quiz_threshold, settings.mastery_recalls_required)


def log_config(store: Store, user_id: int) -> None:
    """Record the thresholds in force so a change is auditable; skips if unchanged."""
    cfg = asdict(_config())
    last = store.events_for(user_id, "mastery_config")
    if not last or json.loads(last[-1]["data_json"]) != cfg:
        store.log_event(user_id, "mastery_config", json.dumps(cfg))


def compute_state(store: Store, lesson: Lesson, user_id: int, now: datetime) -> State:
    """Evidence newer than `now` is ignored. A lesson with no quiz never reaches mastered."""
    cfg = _config()
    lid = lesson.id
    attempts = [a for a in store.attempts_for(user_id, lid) if a["created_at"] <= now.isoformat()]
    check = store.last_check(user_id, lid)
    if not (
        attempts
        or check
        or store.chat_history(user_id, lid, 1)
        or any(store.grades_for(user_id, lid, q.id) for q in lesson.deeper)
    ):
        return "notstarted"
    quiz = [a for a in attempts if a["kind"] == "quiz"]
    if score(quiz, lesson.quiz) < cfg.quiz_threshold:
        return "learning"
    if lesson.task_kind and not (check and check["passed"]):
        return "learning"
    revealed = {e["created_at"][:10] for e in store.events_for(user_id, "reveal", lid)}
    for concept in {q.concept for q in lesson.quiz}:
        ids = {q.id for q in lesson.quiz if q.concept == concept}
        days = {
            a["created_at"][:10]
            for a in attempts
            if a["item_id"] in ids
            and a["kind"] in ("quiz", "review")
            and a["correct"]
            and a["try_no"] == 1
        }
        if len(days - revealed) < cfg.recalls_required:
            return "learning"
    return "mastered"


def refresh(store: Store, lessons: dict[str, Lesson], user_id: int) -> dict[str, State]:
    """Recompute every lesson, save changes and log each transition."""
    now = datetime.now(UTC)
    before = store.mastery_for(user_id)
    out: dict[str, State] = {}
    for lid, lesson in lessons.items():
        out[lid] = state = compute_state(store, lesson, user_id, now)
        old = before.get(lid, "notstarted")
        if state != old:
            store.set_mastery(user_id, lid, state)
            data = {"lesson_id": lid, "from": old, "to": state}
            store.log_event(user_id, "mastery_changed", json.dumps(data))
    return out
