from collections.abc import Callable

from evals_task import ShorterThanInput, make_dataset, run, summarize
from pydantic_ai import models
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import Contains, Evaluator
from pydantic_evals.reporting import EvaluationReport

models.ALLOW_MODEL_REQUESTS = False  # no test here may reach a real model


def check_length(task: Callable[[str], str]) -> bool:
    """Run only ShorterThanInput on one case and return its pass/fail mark."""
    dataset = Dataset(
        name="length",
        cases=[Case(name="c", inputs="hello world")],
        evaluators=[ShorterThanInput()],
    )
    report = dataset.evaluate_sync(task, progress=False)
    case = report.cases[0]
    assert case.evaluator_failures == [], "ShorterThanInput raised an error"
    return case.assertions["ShorterThanInput"].value


def test_shorter_than_input_is_an_evaluator() -> None:
    assert issubclass(ShorterThanInput, Evaluator)


def test_shorter_than_input_passes_only_for_a_shorter_output() -> None:
    assert check_length(lambda text: text[:5]) is True, "a shorter output should pass"
    assert check_length(lambda text: text) is False, "an output as long as the input must fail"
    assert check_length(lambda text: text + "!") is False, "a longer output must fail"


def test_dataset_has_four_complete_cases() -> None:
    dataset = make_dataset()
    assert len(dataset.cases) == 4, "make_dataset() must return exactly 4 cases"
    for case in dataset.cases:
        assert case.name, "every case needs a name"
        assert isinstance(case.inputs, str) and case.inputs.count(". ") >= 1, (
            f"case {case.name!r}: the input needs two sentences, with '. ' between them"
        )
        assert isinstance(case.expected_output, str), f"case {case.name!r}: set expected_output"
        assert case.metadata, f"case {case.name!r}: set metadata, for example {{'topic': 'food'}}"
        contains = [e for e in case.evaluators if isinstance(e, Contains)]
        assert contains, f"case {case.name!r}: add its own Contains(value=...) to evaluators"
        for e in contains:
            assert e.value, f"case {case.name!r}: Contains needs a non-empty value"
            assert e.value in case.expected_output, (
                f"case {case.name!r}: the Contains value should appear in expected_output"
            )


def test_expected_outputs_match_the_task() -> None:
    for case in make_dataset().cases:
        assert summarize(case.inputs) == case.expected_output, (
            f"case {case.name!r}: expected_output should be what summarize() returns"
        )


def test_every_case_passes_every_check() -> None:
    report = make_dataset().evaluate_sync(summarize, progress=False)
    assert len(report.cases) == 4
    assert report.failures == [], "the task raised an error for some case"
    for case in report.cases:
        assert case.evaluator_failures == [], f"case {case.name!r}: an evaluator raised an error"
        assert "ShorterThanInput" in case.assertions, f"case {case.name!r}: no ShorterThanInput"
        assert "Contains" in case.assertions, f"case {case.name!r}: no Contains check"
        failed = [name for name, result in case.assertions.items() if not result.value]
        assert failed == [], f"case {case.name!r} failed: {failed}"


def test_run_returns_the_report() -> None:
    report = run()
    assert isinstance(report, EvaluationReport)
    assert len(report.cases) == 4
    assert report.failures == []
