---
id: gh2-first-ci
track: github
title: "Your first CI workflow"
minutes: 30
pins:
  actions/checkout: "v7.0.1"
  astral-sh/setup-uv: "v10.3.0"
sources:
  - github-actions-get-started-quickstart
  - github-actions-get-started-understand-github-actions
  - github-actions-reference-workflows-and-actions-workflow-syntax
  - github-actions-reference-workflows-and-actions-events-that-trigger-workflows
  - github-actions-tutorials-build-and-test-code-python
  - github-pull-requests-troubleshooting-required-status-checks
  - github-pull-requests-reference-status-checks
---
CI means "continuous integration". Every change gets built and tested by a machine before it can be merged. On GitHub, that machine work is called Actions. In this lesson you read one real workflow, learn the few keys that matter, and then add one to your own practice repo.

You do not run a workflow on your laptop. GitHub runs it on its own machines when something happens in your repo.

## What a workflow is

A workflow is one YAML file in the folder `.github/workflows/` of your repo. A repo can have many. GitHub reads each file and decides when to run it. ([Understanding GitHub Actions](https://docs.github.com/en/actions/get-started/understand-github-actions))

A workflow has four parts, from the outside in:

- **Event.** Something that happens, such as a pull request being opened. Events live under the `on:` key. A workflow with no `on:` never runs.
- **Job.** A list of steps that run together on one machine. Jobs run in parallel unless you say one `needs:` another.
- **Runner.** The machine that runs one job. `runs-on: ubuntu-latest` asks for a fresh Linux virtual machine. When the job ends, the machine is thrown away.
- **Step.** One unit of work. A step is either `run:` (a shell command) or `uses:` (a ready-made action, which is a reusable piece of code that someone else wrote).

The two step kinds get mixed up all the time. `run: pytest` types a command into a shell. `uses: actions/checkout@...` loads an action. Never put a shell command after `uses:`.

Each job has an id (the key under `jobs:`) and an optional `name:`. The name is what you see in the web page and in the pull request checks list. Remember this. It matters again in the required-check section. ([Workflow syntax: `jobs`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobs))

## The events you will use

You will use four triggers most of the time. ([Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows))

- **`pull_request`.** Runs when a pull request is opened, reopened, or gets new commits. This is your main CI trigger. The run tests the merge result (your branch merged into the base), not only your branch. If the pull request has a merge conflict, the run does not start.
- **`push` with `branches: [main]`.** Runs when commits land on main. Use it to check that main is still green after a merge. Without the branch filter, every push to every branch would start a run, and a pull request branch would be tested twice.
- **`workflow_dispatch`.** A manual "Run workflow" button, and `gh workflow run`. The workflow file must be on the default branch for the button to show. A check made by a manual run does not count for a pull request ([GitHub Docs, Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks)).
- **`schedule`.** Runs on a cron timetable, such as `"17 3 * * 1"`. It has caveats. It only runs from the default branch. It uses UTC unless you set `timezone`. The shortest gap is 5 minutes. Runs can be late, especially at the start of an hour, so pick an odd minute. In a public repo, GitHub turns a scheduled workflow off after 60 days with no repo activity.

Here is the trigger block you will use in this lesson:

```yaml
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:
```

A trigger can also have filters, like `paths:`. Be careful with them on a workflow you plan to make a required check. If a filter stops the workflow from starting, the check never appears, and the pull request waits for it forever ([GitHub Docs, Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks)).

## A minimal Python job with uv

This repo's own CI file is a good worked example. It is short. Read it top to bottom. ([Building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) shows the same idea with pip.)

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
jobs:
  checks:
    name: checks
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
        with:
          version: "0.13.1"
          enable-cache: true
      - run: uv sync --locked --all-groups
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run ty check
      - run: uv run pytest -q
```

Line by line:

- `name: CI` is the label of the whole workflow in the Actions tab.
- `on:` is the trigger block from the last section. The `permissions` and `concurrency` blocks come in the next section.
- `jobs: checks:` is one job with the id `checks`. `name: checks` gives it the same display name on purpose.
- `timeout-minutes: 15` stops a stuck job from burning minutes. The default is 360.
- `actions/checkout` copies your repo onto the empty runner. Without it, the machine has none of your files. `persist-credentials: false` stops the action from leaving the token in the git config, where a later step could read it.
- `astral-sh/setup-uv` installs uv. `version` pins the uv version, and `enable-cache` saves downloaded packages between runs.
- `uv sync --locked --all-groups` installs the packages. `--locked` fails the step if `uv.lock` does not match `pyproject.toml`. That is what you want in CI. It stops you from testing different versions than the ones you committed.
- `ruff check`, `ruff format --check`, `ty check` and `pytest -q` are your checks. Each `run:` step must exit with code 0. The first one that exits with a non-zero code fails the job, and later steps are skipped.

Look at the two `uses:` lines. They end in a 40-character commit SHA, with the human-readable tag in a comment. A tag like `v7.0.1` is a label that its owner can move to different code later. A full SHA cannot be moved. If an action's repo is hacked, your pinned workflow still runs the old, reviewed code. The comment lets a person read the version. Dependabot reads the same comment. When it opens a pull request to update the action, it changes both the SHA and the comment. Note that `setup-uv` has no floating `v10` tag at all, so a SHA is the safe way to use it.

## Least privilege and concurrency

Every run gets a temporary token called `GITHUB_TOKEN`. It lets the workflow call the GitHub API. By default it may be able to do more than your job needs. The `permissions:` key lets you shrink it. ([Workflow syntax: `permissions`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions))

```yaml
permissions:
  contents: read
```

Two rules to remember. If you list any permission, every permission you did not list becomes `none`. And `write` includes `read`. A CI job that only reads the code needs only `contents: read`. If a step later gets hijacked, the damage it can do is small. Add a `write` permission only to the one job that needs it.

`concurrency:` stops runs from piling up. All runs with the same `group` string share one slot. By default a waiting run is replaced by a newer waiting run. With `cancel-in-progress: true`, the run that is already running is also cancelled. ([Workflow syntax: `concurrency`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency))

In this repo's file, the group is the workflow name plus the pull request number. When you push a new commit to a pull request, the old run for that pull request is cancelled and a new one starts. The run is only cancelled for pull requests. A push to main is never cancelled halfway, so main always gets a full result.

## Making the job a required check

A passing CI run only protects you if the merge is blocked when it fails. You do that with a rule in your ruleset: required status checks.

The rule lists a check by **name**, and the name of an Actions check is the job name. If the job has `name: checks`, the check is called `checks`. If the job has no `name:`, the check is called after the job id. The rule matches the text exactly. `Checks`, `check` and `test` are all different names.

In the ruleset, you also set `integration_id` to `15368`. That is the id of the GitHub Actions app. It means "only accept this check if Actions reported it". A different app cannot fake the check by using the same name.

Now the confusing part. A pull request can show **Waiting for status to be reported** forever. It means: the rule asks for a check, and no check with that name has been reported for this commit. The usual causes are:

- The name in the rule does not match the job name. A typo is enough.
- The workflow never started. It has no `on:` key, it has no `pull_request` trigger, or a `paths:` or `branches:` filter kept it from running.
- The workflow file has a YAML error, so GitHub could not read it.

One more rule that surprises people. A job that is skipped by an `if:` condition counts as a success. A whole workflow that is skipped by a filter does not. In that case the check just never appears.

Also keep job names unique across all your workflows. Two workflows that both have a job called `checks` make the required check ambiguous. For more on this, read [Status checks](https://docs.github.com/en/pull-requests/reference/status-checks) and [GitHub Docs, Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks).

Create the workflow and let it run once before you add the rule. That way you can see the exact check name first.

## Reading a failed run

When a check turns red, do not guess. Read the log. You can do all of it in the terminal in VS Code. ([Quickstart](https://docs.github.com/en/actions/get-started/quickstart) shows the web view.)

```bash
gh pr checks --watch        # follow the checks on the current PR until they finish
gh run list --limit 5       # recent runs: status, branch, and run id
gh run view <run-id>        # which job and which step failed
gh run view <run-id> --log-failed   # only the log of the failed steps
```

Work like this:

1. Find the first red step. Later red steps are often just the result of the first one.
2. Read the last 20 lines of that step's log. The error is usually right above the exit code.
3. Run the same command on your laptop, for example `uv run pytest -q`. If it fails there too, fix the code. If it passes there, look for a difference: a package version, a missing file, or a lock file that is out of date.
4. Push the fix. The pull request run starts again by itself.

A good habit: when CI fails, say in your own words what the log says before you change anything.

**Sources.** GitHub Docs, all adapted and summarized, CC BY 4.0, read 2026-10-14. This site is not affiliated with GitHub.
[Quickstart for GitHub Actions](https://docs.github.com/en/actions/get-started/quickstart) ·
[Understanding GitHub Actions](https://docs.github.com/en/actions/get-started/understand-github-actions) ·
[Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) ·
[Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) ·
[Building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python) ·
[Status checks](https://docs.github.com/en/pull-requests/reference/status-checks).
Content licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
