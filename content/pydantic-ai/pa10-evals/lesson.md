---
id: pa10-evals
track: pydantic-ai
title: "Evals and LLM-as-judge"
minutes: 35
pins:
  pydantic-ai: "2.56.0"
  pydantic-evals: "2.56.0"
sources:
  - pydantic-ai-evals-evals
  - pydantic-ai-evals-getting-started-quick-start
  - pydantic-ai-evals-evaluators-llm-judge
  - pydantic-ai-evals-evaluators-standard-quality-metrics
---

You change a prompt. The agent now answers the new question well. Did it break an old one? You cannot tell by reading three replies. An **eval** is a small test run for an AI task that you can repeat after every change. In this lesson you build a dataset of cases, score a task with built-in checks and your own, read the report, meet the LLM judge, handle flaky tasks, keep cases in a YAML file, and run it all without an API key. At the end you read how this site checks its own grader. We ran every example on `pydantic-evals` 2.56.0 and `pydantic-ai` 2.56.0 with scripted models only. We never called a real model. Where a point comes only from the docs, the text says so.

## Why run evals

Prompts, rubrics and models change. Each change can fix one answer and spoil another. A unit test cannot catch this well, because a model rarely writes the same text twice. But you can still check properties of the output: is it shorter than the input, does it mention the key word, does a judge say it follows the rubric. An eval runs those checks on many cases and gives you numbers to compare before and after a change.

The [Pydantic Evals overview](https://pydantic.dev/docs/ai/evals/evals/) uses a unit-testing picture. A **case** plus its **evaluators** is one test. A **dataset** is the test suite. Running the suite on your function is an **experiment**, and you get a **report** back. The same page says that evals are still an emerging practice, so treat any rule about them as advice and not as law.

Two details about the package. The docs say `pydantic-evals` does not depend on `pydantic-ai`, and that any function can be the thing you test. We checked the 2.56.0 wheel: it does require `pydantic-ai-slim==2.56.0`, the core package, so `Agent`, `TestModel` and `FunctionModel` come with it. This repo pins both packages at 2.56.0.

Our running example is a tiny task, `summarize`. It returns the first sentence of a text. It is plain Python, so every run is free and the same each time.

```python
def summarize(text: str) -> str:
    first = text.split(". ")[0]
    return first if first.endswith(".") else first + "."
```

## Datasets and cases

A `Dataset` holds `Case` objects and the evaluators that score them. The [Quick Start](https://pydantic.dev/docs/ai/evals/getting-started/quick-start/) shows the same shape.

```python
from pydantic_evals import Case, Dataset

dataset = Dataset(
    name="summaries",
    cases=[
        Case(
            name="tea",
            inputs="Tea is a drink made from leaves. It is popular in many countries.",
            expected_output="Tea is a drink made from leaves.",
            metadata={"topic": "food"},
        ),
    ],
    evaluators=[...],
)
```

- `name` on `Dataset` is required, and you must pass it as a keyword. Leave it out and Python raises `TypeError: Dataset.__init__() missing 1 required keyword-only argument: 'name'`.
- A `Case` has `inputs` (what the task receives), and optionally `name`, `expected_output`, `metadata` and its own `evaluators`. A case without a name shows up in the report as `Case 1`, `Case 2` and so on, by its position.
- Two cases with the same name raise `ValueError: Duplicate case name` when you build the `Dataset`.
- `evaluators=[...]` on the `Dataset` run on every case. `evaluators=[...]` on a `Case` run on that case only. In the report, the case's own checks come first.

The next sections fill in the evaluators.

## Built-in evaluators

Four built-in evaluators cover the common cheap checks. All of them live in `pydantic_evals.evaluators`, and each gives a pass or fail mark.

| Evaluator | Passes when | A detail we saw |
|---|---|---|
| `EqualsExpected()` | the output equals the case's `expected_output` | A case with no `expected_output` gets no mark at all from it. |
| `Contains(value="Tea")` | the output contains `value` | It checks for the `value` you pass. It does not read `expected_output`. It works on strings, lists and dicts. `case_sensitive` only matters when both sides are strings. |
| `IsInstance(type_name="str")` | the output's class, or one of its parent classes, has that name | You give the type's name as a string, not the type. On a miss the reason reads `output is of type str`. |
| `MaxDuration(seconds=1.0)` | the task took at most that many seconds | In our run a task that slept 0.05 s failed `MaxDuration(seconds=0.01)`. |

When two evaluators of the same kind give the same default name in one case, the second is renamed with a suffix. We saw `Contains`, `Contains_2` and `Contains_3`.

The docs say to prefer these over a judge when a plain check will do. Use `IsInstance` for format, `EqualsExpected` for exact match and `MaxDuration` for speed. Save the judge for qualities that code cannot see.

## Writing your own evaluator

Subclass `Evaluator`, add `@dataclass`, and write `evaluate(self, ctx)`. The `ctx` is an `EvaluatorContext`. These fields are the ones you use most: `ctx.inputs`, `ctx.output`, `ctx.expected_output`, `ctx.metadata` and `ctx.duration`.

```python
from dataclasses import dataclass

from pydantic_evals.evaluators import Evaluator, EvaluatorContext


@dataclass
class ShorterThanInput(Evaluator[str, str]):
    def evaluate(self, ctx: EvaluatorContext[str, str]) -> bool:
        return len(ctx.output) < len(ctx.inputs)
```

The type you return decides where the result lands in the report. We ran one evaluator of each kind to see it.

| `evaluate` returns | It shows up as |
|---|---|
| `bool` | an **assertion**: a pass or fail mark |
| `int` or `float` | a **score**: a number |
| `str` | a **label**: a category |
| `EvaluationReason(value=..., reason="...")` | the same, plus a reason text |
| a `dict` of those | several results at once, one per key |

The result takes the class name as its name (`ShorterThanInput`). Dict keys name their own results. The method can also be `async def`. We ran that too.

Make the check a bool when it is a yes or no, like here. Return a score when you want to see "how good", for example the ratio `len(output) / len(inputs)`.

Plug the evaluators in, run the dataset, and the pieces meet:

```python
from pydantic_evals.evaluators import Contains, EqualsExpected, IsInstance, MaxDuration

dataset = Dataset(
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
        ),
        Case(name="short", inputs="Hello.", expected_output="Hello."),
        Case(inputs="Cats sleep a lot. They also hunt."),
    ],
    evaluators=[
        EqualsExpected(),
        IsInstance(type_name="str"),
        MaxDuration(seconds=1.0),
        ShorterThanInput(),
    ],
)
```

Case `short` has a one-sentence input. `summarize` gives it back unchanged, so `ShorterThanInput` should fail for it. That is the evaluator doing its job.

## Reading the report

`evaluate_sync` runs the task on every case and gives you a report. `report.print()` shows it as a table.

```python
report = dataset.evaluate_sync(summarize, progress=False)
report.print(include_durations=False)
```

```text
   Evaluation Summary:
        summarize
┏━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Case ID  ┃ Assertions ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━┩
│ tea      │ ✔✔✔✔✔      │
│ rain     │ ✔✔✔✔       │
│ short    │ ✔✔✔✗       │
│ Case 4   │ ✔✔✔        │
│ Averages │ 93.8% ✔    │
└──────────┴────────────┘
```

(We removed the lines between the rows to save space.) How to read it:

- The title uses the task function's name.
- The **Assertions** column has one mark per check, with no names. Case `tea` has five marks because it has its own `Contains` plus four dataset checks. Case `rain` has four. Case `Case 4` has three, because `EqualsExpected` skips a case with no expected output.
- A score or a label column appears only when some evaluator produced one.
- The **Averages** row is the share of all checks that passed. Here 15 of 16 passed, which is 93.8%. It counts checks, not cases.
- `progress=False` hides the progress bar. `include_durations=False` hides the time column, which changes on every run. Other switches are `include_input=True`, `include_output=True`, `include_expected_output=True` and `include_reasons=True`.

The table does not say which check failed. To find out, read the report as data:

```python
for case in report.cases:
    print(case.name, {name: result.value for name, result in case.assertions.items()})
print(report.averages().assertions)  # 0.9375
```

Each item in `report.cases` has `assertions`, `scores`, `labels`, `output`, `expected_output` and `evaluator_failures`. In our run `short` printed `'ShorterThanInput': False` and the other three checks `True`.

**Errors do not stop the run.** In our runs, `evaluate_sync` did not raise when a task or an evaluator failed. We saw two kinds of error.

- **The task raised.** The case moves to `report.failures`, which has its `name` and `error_message`. It is not in `report.cases` and not in the averages. The table prints a second block, "Case Failures".
- **An evaluator raised.** The case stays in `report.cases`. The error sits in `case.evaluator_failures`, there is an "Evaluator Failures" column, and that evaluator gives no mark.

So "no ✗ in the table" does not mean "all passed". A gate that is safe checks all three things:

```python
def all_good(report) -> bool:
    return (
        not report.failures
        and all(not c.evaluator_failures for c in report.cases)
        and all(a.value for c in report.cases for a in c.assertions.values())
    )
```

On the report above this returns `False`, because of `short`. A task or an evaluator that crashed would also give `False`.

## LLM as a judge

Some qualities need judgment. Is the summary faithful? Is the tone polite? Code cannot tell. `LLMJudge` asks a model. You write a **rubric**: a statement that is true or false for the output. The [LLM Judge page](https://pydantic.dev/docs/ai/evals/evaluators/llm-judge/) has more.

```python
from pydantic_evals.evaluators import LLMJudge

LLMJudge(
    rubric="The summary keeps the main fact of the input.",
    model="anthropic:claude-sonnet-4-6",
    include_input=True,
)
```

What the judge sees is up to you:

- By default it gets the output and the rubric. Nothing else.
- `include_input=True` adds the case's inputs. `include_expected_output=True` adds the expected output.
- We caught the prompt a scripted judge model received. It holds tagged blocks: `<Input>`, `<Output>`, `<ExpectedOutput>` (only when asked for) and `<Rubric>`.

What it returns:

- By default one **assertion** with a reason. The reason shows with `report.print(include_reasons=True)`.
- `score={}` adds a number from 0.0 to 1.0. `assertion=False` drops the pass or fail mark.
- Name the results with `assertion={"evaluation_name": "faithful"}`. Without names, a judge with both outputs used `LLMJudge_score` and `LLMJudge_pass`.

The docs give advice you can use:

- Write a specific rubric. "Good response" is too vague. "Response answers the question without inventing facts" is better.
- Use several narrow judges, one per quality, and not one broad rubric.
- Put cheap deterministic checks next to the judge. Do not ask a model what code can decide.
- A judge is not deterministic, it costs money, and it has biases such as liking longer answers. The docs suggest checking a judge against human labels. The last section shows this site doing that.

The [Standard Quality Metrics](https://pydantic.dev/docs/ai/evals/evaluators/standard-quality-metrics/) page shows two more shapes. `GEval` takes criteria and a list of steps, and gives an integer score on a scale you choose. The page also lists ready-made `LLMJudge` rubrics for retrieval and answer quality (faithfulness, answer relevance, context precision, context recall). The page says they approximate the published methods with one judge call each. We did not run these.

## Always set the judge model

If you leave out `model=`, `LLMJudge` uses a default judge model. In 2.56.0 that default is `openai:gpt-5.2`. The docs say so, the class docstring says so, and the module value we read says so. This has three effects.

- Your eval needs an OpenAI key, even if everything else in your project uses another provider.
- You pay for a model you did not pick.
- Scores from different judge models are not comparable.

So always choose the judge yourself. There are two ways.

```python
from pydantic_evals.evaluators.llm_as_a_judge import set_default_judge_model

set_default_judge_model("anthropic:claude-sonnet-4-6")  # every LLMJudge without its own model
LLMJudge(rubric="...", model="anthropic:claude-sonnet-4-6")  # one evaluator
```

Call `set_default_judge_model` before you run the dataset. In our run, a judge without `model=` used the scripted model we had set. Put the judge model in your config, as this site does with `JUDGE_MODEL`.

Here is what happens when you forget. We ran a dataset with `LLMJudge(rubric=...)` and no model, with the API keys removed and `ALLOW_MODEL_REQUESTS = False`, so nothing could be sent. Observed result:

- Nothing raised. `report.failures` was `[]`.
- The case had no assertion. `report.averages().assertions` was `None`.
- The table showed only an "Evaluator Failures" column: `LLMJudge: UserError: Set the `OPENAI_API_KEY` environment variable ...`.

A missing judge looks like a quiet report, not a red one. This is why the gate in the last section checks `evaluator_failures`.

## Flaky tasks and repeat

A task that calls a model can give a different answer each time. One run can look fine by luck. `repeat=3` runs every case three times.

```python
import itertools

calls = itertools.count(1)


def flaky(text: str) -> str:
    return "oops" if next(calls) % 3 == 0 else text.upper()  # every third call is wrong


flaky_set = Dataset(
    name="flaky",
    cases=[
        Case(name="a", inputs="x", expected_output="X"),
        Case(name="b", inputs="y", expected_output="Y"),
    ],
    evaluators=[EqualsExpected()],
)
report = flaky_set.evaluate_sync(flaky, progress=False, repeat=3, max_concurrency=1)
report.print(include_durations=False)
```

With two cases and `repeat=3` we saw:

```text
┃ Case ID  ┃ Assertions ┃
│ a [1/3]  │ ✔          │
│ a [2/3]  │ ✔          │
│ a [3/3]  │ ✗          │
│ b [1/3]  │ ✔          │
│ b [2/3]  │ ✔          │
│ b [3/3]  │ ✗          │
│ Averages │ 66.7% ✔    │
```

- Each run is its own row, named `case [run/total]`.
- `report.case_groups()` groups the runs of one case. Each group has a `name`, its `runs`, and a `summary` with averages. Both of our cases scored 0.67.
- The Averages row covers all runs. It is your estimate of how often the task is right.
- `max_concurrency=1` made the calls run one at a time, so our counter-based demo came out in a fixed order. By default all cases run at once. A plain (non-async) task function ran in a worker thread when we looked at a traceback.
- Repeats multiply the cost. Three runs of a task and a judge is three times the model calls.

## YAML datasets

You can keep cases in a file, away from the code. `to_file` saves and `from_file` loads. A custom evaluator must be listed in `custom_evaluator_types` both ways.

```python
dataset.to_file("summaries.yaml", custom_evaluator_types=[ShorterThanInput])
loaded = Dataset[str, str, dict[str, str]].from_file(
    "summaries.yaml", custom_evaluator_types=[ShorterThanInput]
)
```

The file we got:

```yaml
# yaml-language-server: $schema=summaries_schema.json
name: summaries
cases:
- name: tea
  inputs: Tea is a drink. It is hot.
  metadata: null
  expected_output: Tea is a drink.
  evaluators: []
- name: rain
  inputs: Rain falls. Farmers smile.
  metadata: null
  expected_output: null
  evaluators:
  - Contains: Rain
evaluators:
- EqualsExpected
- ShorterThanInput
report_evaluators: []
```

- An evaluator without arguments is just its name. One with a single argument can be `Contains: Rain`. We also loaded a hand-written file with the long form (`Contains: {value: hello, case_sensitive: false}`) and an `LLMJudge` with `rubric`, `model` and `include_input`. Putting `model:` in the file pins the judge with the data.
- `to_file` also wrote `summaries_schema.json` next to the file. The first line of the YAML points to it, so an editor can check and complete your file.
- Load without `custom_evaluator_types` and you get an `ExceptionGroup`. Inside it the message says ``Evaluator 'ShorterThanInput' is not in the provided `custom_evaluator_types`. Valid choices: [...]``, with the built-in names in the list.
- Give the dataset a metadata type when you save it, as we did with `dict[str, str]`. With `Dataset[str, str, None]`, `to_file` raised ``Dataset` is not fully defined; you should define `meta_type`, then call `Dataset.model_rebuild()`.``

The [Dataset Management](https://pydantic.dev/docs/ai/evals/how-to/dataset-management/) page covers saving, loading and generating datasets. It is linked only. It is not one of this site's registered sources.

## Running offline

The task can be any function, `def` or `async def`. For an agent, wrap the run. Build the agent on a `FunctionModel` (or `TestModel`) and set `ALLOW_MODEL_REQUESTS = False`, as in the lesson on tools and dependencies.

```python
def reply(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    prompt = str(messages[-1].parts[-1].content)
    return ModelResponse(parts=[TextPart(prompt.split(". ")[0] + ".")])


agent = Agent(FunctionModel(reply))


async def task(text: str) -> str:
    result = await agent.run(text)
    return result.output


report = loaded.evaluate_sync(task, progress=False)
```

All checks on both cases passed. A few things we ran into:

- A `FunctionModel` function must return a `ModelResponse`. We first returned a plain string and got an `AssertionError`.
- You can run a judge offline too. Pass a `FunctionModel` as `model=`. It is not a real model, so the block on real requests does not stop it. The function gets the judge prompt and must call the output tool with `reason`, `pass` and `score`. Our scripted judge always said pass. That tests the wiring only. It says nothing about how good a real judge would be.
- `evaluate_sync` cannot run inside a running event loop. Inside `async` code it raised `RuntimeError: This event loop is already running`. Use `await dataset.evaluate(task)` there. This site's calibration script does that.
- On Python 3.13 we saw a `DeprecationWarning: There is no current event loop` from `pydantic_evals` in a pytest run. The run still passed.

A test for your dataset is the gate from before (`make_dataset` is a function that builds the dataset, like the one you write in the task):

```python
def test_summaries() -> None:
    report = make_dataset().evaluate_sync(summarize, progress=False)
    assert all_good(report)
```

## How this site calibrates its grader

The think-deeper grader in `app/agents/grader.py` marks each rubric criterion as met or not met. If someone changes a rubric or the grader prompt, will it still agree with a human? The files for this check are `evals/run_grader.py`, `evals/grader_dataset.yaml` and `.github/workflows/evals.yml`.

**The data.** `grader_dataset.yaml` holds five answers to one question, labelled by hand. The file's header calls the labels owner-labelled. Each answer lists, per criterion (`reuse`, `tests`, `scope`), whether a careful human would mark it met. The five answers are traps on purpose: a good answer, a long answer that says nothing (`verbose-wrong`), a prompt injection, a short right answer (`terse-right`) and a right answer in other words (`synonym`). It is not the pydantic-evals YAML format from the last section. It is a plain list that the script reads with `yaml.safe_load` and turns into `Case` objects. The question itself comes from a test fixture, `fx-demo`.

**The run.** `run_grader.py` builds `Dataset(name="grader-calibration", ...)`. Each `Case` has the answer as `inputs` and the labels as `expected_output`. The one evaluator is `MetAgreement`, a custom `Evaluator` that returns a float: the share of criteria where the grader's `met` flag equals the label. The task calls the real `grade_answer`, which reads each answer three times and takes the majority (2 of 3) per criterion. The task keeps only the final `met` flags. The script runs `await dataset.evaluate(task)`, prints the report, and then prints **Cohen's kappa** over all criterion labels (15 here) against a target of 0.7.

Why kappa and not plain agreement? Kappa takes away the agreement you would get by luck. We ran the script's own `build_dataset()` and `kappa()` offline with two scripted graders. One copied the labels: agreement 100%, kappa 1.00. One said "met" for everything: agreement 60%, because 9 of the 15 labels are true, but kappa 0.00. The second grader learned nothing, and kappa shows it. The spec asks for 0.7 per criterion. The script prints one number over all labels, and with only 15 labels that number is rough. Five answers are a start, not proof.

**The judge model.** The script calls `set_default_judge_model(settings.judge_model)` before it runs. `JUDGE_MODEL` defaults to an OpenRouter Claude model. Today the dataset has no `LLMJudge`, because `MetAgreement` is plain Python, so the call changes nothing yet. The project spec (`docs/SPEC.md`, section 12) says the judge model is set explicitly because the default would be `openai:gpt-5.2`. So an `LLMJudge` added later will use the project's judge.

**Where it runs.** The calibration calls a real model, three times per answer, so it costs tokens and needs the owner's OpenRouter key. The workflow `evals.yml` starts only on `workflow_dispatch`, which means someone presses the button. It runs `uv run python -m evals.run_grader` with the `OPENROUTER_API_KEY` secret. The CI workflow (`ci.yml`) does not run it, and when we wrote this lesson no test imported `run_grader`. We did not run the real calibration for this lesson. We ran its pieces offline, as above.

Sources: [Pydantic Evals overview](https://pydantic.dev/docs/ai/evals/evals/), [Quick Start](https://pydantic.dev/docs/ai/evals/getting-started/quick-start/), [LLM Judge](https://pydantic.dev/docs/ai/evals/evaluators/llm-judge/) and [Standard Quality Metrics](https://pydantic.dev/docs/ai/evals/evaluators/standard-quality-metrics/) from the Pydantic AI documentation, version 2.56.0, MIT licence, © Pydantic Services Inc. 2024 to present. The Dataset Management page is linked only. This site is not affiliated with Pydantic.
