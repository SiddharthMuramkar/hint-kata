"""Task: score a small summarizer with an eval (dataset, cases, evaluators, report)."""

from dataclasses import dataclass

from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Contains, EqualsExpected, Evaluator, EvaluatorContext
from pydantic_evals.reporting import EvaluationReport


def summarize(text: str) -> str:
    """The task under test, already written: return the first sentence of `text`."""
    first = text.split(". ")[0]
    return first if first.endswith(".") else first + "."


@dataclass
class ShorterThanInput(Evaluator[str, str, dict[str, str]]):
    """Pass when the output is shorter than the input."""

    def evaluate(self, ctx: EvaluatorContext[str, str, dict[str, str]]) -> bool:
        return len(ctx.output) < len(ctx.inputs)


def make_dataset() -> Dataset[str, str, dict[str, str]]:
    """Four cases. Every input has two sentences, so a good summary is shorter than the input."""
    return Dataset(
        name="summaries",
        cases=[
            Case(
                name="tea",
                inputs="Tea is a drink made from leaves. It is popular in many countries.",
                expected_output="Tea is a drink made from leaves.",
                metadata={"topic": "food"},
                evaluators=[Contains(value="Tea")],
            ),
            Case(
                name="rain",
                inputs="Rain falls when clouds get heavy. Farmers wait for it every spring.",
                expected_output="Rain falls when clouds get heavy.",
                metadata={"topic": "weather"},
                evaluators=[Contains(value="Rain")],
            ),
            Case(
                name="python",
                inputs="Python is a programming language. Many beginners start with it.",
                expected_output="Python is a programming language.",
                metadata={"topic": "code"},
                evaluators=[Contains(value="Python")],
            ),
            Case(
                name="moon",
                inputs="The Moon circles the Earth. It takes about a month to do so.",
                expected_output="The Moon circles the Earth.",
                metadata={"topic": "space"},
                evaluators=[Contains(value="Moon")],
            ),
        ],
        evaluators=[EqualsExpected(), ShorterThanInput()],
    )


def run() -> EvaluationReport[str, str, dict[str, str]]:
    """Evaluate `summarize` on the dataset and return the report."""
    return make_dataset().evaluate_sync(summarize, progress=False)
