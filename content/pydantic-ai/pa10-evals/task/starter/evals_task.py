"""Task: score a small summarizer with an eval (dataset, cases, evaluators, report)."""

from dataclasses import dataclass

from pydantic_evals import Case, Dataset  # noqa: F401  (you will use Case)
from pydantic_evals.evaluators import (  # noqa: F401  (you will use these)
    Contains,
    EqualsExpected,
    Evaluator,
    EvaluatorContext,
)
from pydantic_evals.reporting import EvaluationReport


def summarize(text: str) -> str:
    """The task under test, already written: return the first sentence of `text`."""
    first = text.split(". ")[0]
    return first if first.endswith(".") else first + "."


@dataclass
class ShorterThanInput(Evaluator[str, str, dict[str, str]]):
    """Pass when the output is shorter than the input."""

    def evaluate(self, ctx: EvaluatorContext[str, str, dict[str, str]]) -> bool:
        # TODO 1: return True only when the output is SHORTER than the input.
        #   `ctx.output` is what `summarize` returned. `ctx.inputs` is the case's input text.
        #   Compare their lengths. A bool result becomes a pass/fail mark in the report.
        return False


def make_dataset() -> Dataset[str, str, dict[str, str]]:
    """Four cases. Every input must have two sentences, so a good summary is shorter."""
    # TODO 2: build the dataset.
    #   - name="summaries"
    #   - four `Case` objects, each with a unique `name`, `inputs` (two sentences, with ". "
    #     between them), `expected_output` (what `summarize` returns for that input) and
    #     `metadata` (a dict such as {"topic": "food"}).
    #   - give each Case its own `evaluators=[Contains(value=...)]` with a word that must
    #     appear in that case's summary.
    #   - dataset-wide `evaluators=[EqualsExpected(), ShorterThanInput()]`.
    return Dataset(name="summaries", cases=[], evaluators=[])


def run() -> EvaluationReport[str, str, dict[str, str]]:
    """Evaluate `summarize` on the dataset and return the report."""
    # TODO 3: build the dataset with make_dataset(), run `summarize` over it with
    #   `evaluate_sync` (pass progress=False to hide the progress bar) and return the report.
    raise NotImplementedError("finish run()")
