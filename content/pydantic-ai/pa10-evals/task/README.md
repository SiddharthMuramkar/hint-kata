# Task: score a summarizer with an eval

You will write a small eval for a function called `summarize`. It returns the first sentence of a text. It is plain Python, so the eval runs offline and needs no API key.

Open `evals_task.py` in your workspace. `summarize` is already written, so do not change it. The file has three TODO comments.

1. **`ShorterThanInput.evaluate`** (TODO 1): return `True` only when the output is **shorter** than the input.
   - `ctx.output` is what `summarize` returned. `ctx.inputs` is the text the case gave it.
   - Compare their lengths. A `bool` result becomes a pass or fail mark in the report. The section "Writing your own evaluator" shows the same shape.
   - "Shorter" means strictly shorter. An output as long as the input must fail.
2. **`make_dataset()`** (TODO 2): build a `Dataset` named `"summaries"` with **four** cases.
   - Each `Case` needs a unique `name`, an `inputs` text of **two sentences** with `". "` between them, an `expected_output` (exactly what `summarize` returns for that input) and a `metadata` dict such as `{"topic": "food"}`.
   - Give each `Case` its own `evaluators=[Contains(value=...)]`, with a word that must appear in that case's summary.
   - Give the `Dataset` the dataset-wide `evaluators=[EqualsExpected(), ShorterThanInput()]`.
3. **`run()`** (TODO 3): build the dataset with `make_dataset()`, run `summarize` over it with `evaluate_sync`, and return the report. Pass `progress=False` to hide the progress bar. The section "Reading the report" shows the call.

## How the check works

The hidden tests need no API key and never call a model. They check that:

- `ShorterThanInput` is an `Evaluator`. It passes for an output that is shorter, and fails for an output of the same length and for a longer one.
- `make_dataset()` returns exactly four cases. Each has a name, an input of two sentences, an `expected_output`, a `metadata` dict and its own `Contains` evaluator.
- For every case, `summarize(inputs)` equals `expected_output`.
- Running `summarize` over the dataset gives a report with four cases, no task failures, no evaluator failures, and every check passed, including `ShorterThanInput` and `Contains`.
- `run()` returns an `EvaluationReport` with those four cases.

Press **Check my work** when you are ready. If a test fails, read its message and the lesson sections "Datasets and cases", "Built-in evaluators" and "Reading the report".
