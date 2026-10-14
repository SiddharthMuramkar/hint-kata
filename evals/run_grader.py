"""Calibrate the grader against owner-labelled answers. Costs real tokens: never run in CI.

uv run python -m evals.run_grader
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml
from pydantic_ai.models import KnownModelName
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.evaluators.llm_as_a_judge import set_default_judge_model

from app.agents.grader import grade_answer
from app.config import settings
from app.content import DeeperQuestion, load_lessons

HERE = Path(__file__).parent
FIXTURES = HERE.parent / "tests" / "fixtures" / "content"


def kappa(pairs: list[tuple[bool, bool]]) -> float:
    """Cohen's kappa for two raters giving True/False."""
    n = len(pairs)
    if n == 0:
        return 0.0
    observed = sum(a == b for a, b in pairs) / n
    pa = sum(a for a, _ in pairs) / n
    pb = sum(b for _, b in pairs) / n
    expected = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if expected == 1 else (observed - expected) / (1 - expected)


@dataclass
class MetAgreement(Evaluator[str, dict[str, bool], None]):
    """Score = share of criteria where the grader's met flag equals the label."""

    def evaluate(self, ctx: EvaluatorContext[str, dict[str, bool], None]) -> float:
        expected = ctx.expected_output or {}
        got = ctx.output
        return sum(got.get(k) == v for k, v in expected.items()) / max(len(expected), 1)


def load_question() -> DeeperQuestion:
    return next(iter(load_lessons(FIXTURES).values())).deeper[0]


def build_dataset() -> Dataset[str, dict[str, bool], None]:
    raw = yaml.safe_load((HERE / "grader_dataset.yaml").read_text(encoding="utf-8"))
    return Dataset(
        name="grader-calibration",
        cases=[
            Case(name=c["name"], inputs=c["answer"], expected_output=c["expected_met"])
            for c in raw["cases"]
        ],
        evaluators=[MetAgreement()],
    )


async def main() -> None:
    set_default_judge_model(cast(KnownModelName, settings.judge_model))
    question = load_question()

    async def task(answer: str) -> dict[str, bool]:
        outcome = await grade_answer(question, answer)
        return {c.name: c.met for c in outcome.criteria}

    dataset = build_dataset()
    report = await dataset.evaluate(task)
    report.print()
    pairs = [
        (bool(c.output.get(k)), v)
        for c in report.cases
        if c.expected_output
        for k, v in c.expected_output.items()
    ]
    print(f"Cohen's kappa over {len(pairs)} criterion labels: {kappa(pairs):.2f} (target >= 0.7)")


if __name__ == "__main__":
    asyncio.run(main())
