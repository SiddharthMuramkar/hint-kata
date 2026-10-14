"""Grading for quiz items. Pure functions: no I/O, no framework."""

import random
import re
from dataclasses import dataclass
from typing import Any

from app.content import QuizItem


@dataclass
class QuizResult:
    correct: bool
    feedback: str
    misconception: str
    explanation: str
    correct_answer: object


def scramble(item: QuizItem) -> list[int]:
    """The fixed shuffled order the UI shows an `order` item's steps in (never the true order)."""
    shown = list(range(len(item.steps)))
    random.Random(item.id).shuffle(shown)
    if shown == sorted(shown) and len(shown) > 1:
        shown = shown[1:] + shown[:1]
    return shown


def _norm(s: str) -> str:
    return " ".join(s.split()).casefold()


def grade_item(item: QuizItem, answer: object) -> QuizResult:
    """`single`: answer is an option index. `order`: answer lists positions in the scrambled
    display, in the learner's order. `blank`: answer is text."""
    if item.type == "single":
        right = next(i for i, o in enumerate(item.options) if o.correct)
        chosen = (
            item.options[answer]
            if isinstance(answer, int) and 0 <= answer < len(item.options)
            else None
        )
        return QuizResult(
            correct=answer == right and not isinstance(answer, bool),
            feedback=chosen.feedback if chosen else "",
            misconception=chosen.misconception if chosen else "",
            explanation=item.explanation,
            correct_answer=right,
        )
    if item.type == "order":
        shown = scramble(item)
        ok = (
            isinstance(answer, list)
            and sorted(answer) == list(range(len(shown)))
            and [shown[p] for p in answer] == sorted(shown)
        )
        return QuizResult(ok, "", "", item.explanation, [shown.index(i) for i in range(len(shown))])
    text = answer if isinstance(answer, str) else ""
    if item.answer.startswith("re:"):
        ok = re.fullmatch(item.answer[3:], text.strip(), re.IGNORECASE) is not None
    else:
        ok = _norm(text) == _norm(item.answer)
    return QuizResult(ok, "", "", item.explanation, item.answer)


def score(attempts: list[dict[str, Any]], items: list[QuizItem]) -> float:
    """Share of items answered correctly on the first try."""
    first = {a["item_id"] for a in attempts if a["try_no"] == 1 and a["correct"]}
    return sum(i.id in first for i in items) / len(items) if items else 0.0
