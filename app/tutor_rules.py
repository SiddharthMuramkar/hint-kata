"""Hint-ladder rules, enforced by the server. Pure functions; the prompt only describes them."""

import re
from difflib import SequenceMatcher
from typing import Any

LADDER = [
    "L0 restate the goal / ask what was tried",
    "L1 point to the lesson section or doc link",
    "L2 leading question",
    "L3 the approach in words",
    "L4 a worked example on a different problem",
    "L5 code with blanks",
    "L6 full answer",
]

_FENCE = re.compile(r"(`{3,}|~{3,})[^\n]*\n.*?(?:\1|\Z)", re.DOTALL)
_CITATION = re.compile(r"\[§([a-z0-9-]+)\]")


def compute_ceiling(attempts_on_lesson: int, active_quiz: bool, revealed: bool) -> int:
    ceiling = 6 if revealed else min(6, 1 + attempts_on_lesson)
    return min(ceiling, 2) if active_quiz else ceiling


def apply_ceiling(text: str, ceiling: int) -> str:
    """Below L4 no code is allowed: swap every fenced block for a placeholder line."""
    if ceiling >= 4:
        return text
    note = f"[code withheld at hint level L{ceiling} — attempt the task first]"
    return _FENCE.sub(note, text)


def validate_citations(text: str, section_ids: set[str]) -> tuple[str, list[str]]:
    """Drop `[§id]` markers that are not a section of this lesson; return the ordered valid ids."""
    found: list[str] = []

    def keep(m: re.Match[str]) -> str:
        if m[1] not in section_ids:
            return ""
        if m[1] not in found:
            found.append(m[1])
        return m[0]

    return _CITATION.sub(keep, text), found


def no_progress(history: list[dict[str, Any]]) -> bool:
    """True when the learner's last two messages are near-identical: stop asking, name the error."""
    last = [str(m["content"]).casefold().strip() for m in history if m["role"] == "user"][-2:]
    return len(last) == 2 and SequenceMatcher(None, last[0], last[1]).ratio() >= 0.9
