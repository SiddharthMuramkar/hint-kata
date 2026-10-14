"""Spaced review: map answers to fsrs ratings, schedule cards, resolve due cards to content."""

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fsrs import Card, Rating, Scheduler

from app.config import settings
from app.content import Lesson, QuizItem
from app.quiz import QuizResult
from app.store import Store


def item_key(lesson_id: str, item_id: str) -> str:
    return f"{lesson_id}:{item_id}"


def criterion_item_id(question_id: str, criterion_name: str) -> str:
    return f"{question_id}#{re.sub(r'[^a-z0-9]+', '-', criterion_name.lower()).strip('-')}"


def rating_for(
    correct: bool, confidence: str, try_no: int, hint_used: bool, elapsed_ms: int
) -> Rating:
    """SPEC section 9: wrong is Again; a second try, a hint or a guess is Hard; else Good,
    or Easy when the learner was sure and answered in under 10 seconds."""
    if not correct:
        return Rating.Again
    if try_no > 1 or hint_used or confidence == "guessing":
        return Rating.Hard
    if confidence == "sure" and elapsed_ms < 10_000:
        return Rating.Easy
    return Rating.Good


def record_result(
    store: Store,
    user_id: int,
    lesson_id: str,
    item_id: str,
    rating: Rating,
    now: datetime | None = None,
    surprise: bool = False,
) -> str:
    """Review the item's card (creating it if new), save it and a review log. Returns the due
    time as ISO UTC. A surprise (sure but wrong) is never scheduled more than a day out."""
    now = now or datetime.now(UTC)
    key = item_key(lesson_id, item_id)
    row = store.get_card(user_id, key)
    card = (
        Card.from_json(row["card_json"])
        if row
        else Card(card_id=int.from_bytes(hashlib.sha256(f"{user_id}:{key}".encode()).digest()[:6]))
    )
    card, log = Scheduler(desired_retention=settings.desired_retention).review_card(
        card, rating, review_datetime=now
    )
    if surprise:
        card.due = min(card.due, now + timedelta(days=1))
    card_id = store.upsert_card(
        user_id, key, lesson_id, card.to_json(), card.due.isoformat(), int(rating)
    )
    store.add_review_log(card_id, log.to_json())
    return card.due.isoformat()


def record_quiz_attempt(
    store: Store,
    user_id: int,
    lesson_id: str,
    item: QuizItem,
    result: QuizResult,
    confidence: str,
    try_no: int,
    elapsed_ms: int,
) -> str | None:
    """Misses become cards: a wrong first try makes an Again card, a right second try softens
    it to Hard. A right first try, or a second wrong try, changes nothing."""
    if (try_no == 1) == result.correct:
        return None
    rating = rating_for(result.correct, confidence, try_no, False, elapsed_ms)
    return record_result(
        store,
        user_id,
        lesson_id,
        item.id,
        rating,
        surprise=rating == Rating.Again and confidence == "sure",
    )


def record_criterion(
    store: Store,
    user_id: int,
    lesson_id: str,
    question_id: str,
    criterion_name: str,
    met: bool,
    now: datetime | None = None,
) -> str | None:
    """An unmet rubric criterion becomes an Again card; a met one only updates a card that
    already exists (Good)."""
    item_id = criterion_item_id(question_id, criterion_name)
    if met and store.get_card(user_id, item_key(lesson_id, item_id)) is None:
        return None
    rating = Rating.Good if met else Rating.Again
    return record_result(store, user_id, lesson_id, item_id, rating, now)


@dataclass
class DueItem:
    card_id: int
    lesson_id: str
    item_id: str
    lesson_title: str
    prompt: str
    kind: Literal["quiz", "criterion"]
    item: QuizItem | None = None
    criterion_text: str | None = None


def resolve(card: dict[str, Any], lessons: dict[str, Lesson]) -> DueItem | None:
    """Find the content behind a stored card, or None when the lesson or item is gone."""
    lesson = lessons.get(card["lesson_id"])
    if lesson is None:
        return None
    item_id = card["item_key"].removeprefix(f"{lesson.id}:")
    if "#" in item_id:
        for q in lesson.deeper:
            for c in q.rubric:
                if criterion_item_id(q.id, c.name) == item_id:
                    return DueItem(
                        card["id"], lesson.id, item_id, lesson.title, q.prompt, "criterion",
                        criterion_text=c.explanation,
                    )  # fmt: skip
        return None
    quiz = next((q for q in lesson.quiz if q.id == item_id), None)
    if quiz is None:
        return None
    return DueItem(card["id"], lesson.id, item_id, lesson.title, quiz.prompt, "quiz", item=quiz)


def due_items(
    store: Store, lessons: dict[str, Lesson], user_id: int, now: datetime
) -> list[DueItem]:
    cards = store.due_cards(user_id, now.isoformat(), limit=50)
    return [d for c in cards if (d := resolve(c, lessons))]
