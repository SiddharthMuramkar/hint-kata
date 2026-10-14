---
id: gh9-scheduled-automation
track: github
title: "Scheduled automation, concurrency and the merge queue idea"
minutes: 25
pins:
  gh: "2.102"
sources:
  - github-actions-reference-workflows-and-actions-events-that-trigger-workflows
  - github-actions-how-tos-write-workflows-choose-when-workflows-run-trigger-a-workflow
  - github-actions-how-tos-write-workflows-choose-when-workflows-run-control-workflow-concurrency
  - github-actions-reference-workflows-and-actions-workflow-syntax
  - github-repositories-configuring-branches-and-merges-in-your-repository-configuring-pull-request-merges-managing-a-merge-queue
---
So far your workflows ran because a person did something: opened a pull request, or pushed to `main`. This lesson is about workflows that run on their own. You will learn how to run one on a timetable, how to start one by hand, how to stop two runs from trampling each other, and what changes when a robot opens a pull request. You will also meet the merge queue as an idea. Then you read how this repo's weekly docs re-sync uses all of it, and you build a small nightly workflow in your own repo. This site is not affiliated with GitHub. It teaches how GitHub works and links to the official pages.

Three questions run through the lesson. When does it run? How many runs may overlap? Who has to say yes before the checks start?

## Run a workflow on a schedule

The `schedule` trigger starts a workflow at set times, with no person involved. You give it one or more `cron` lines. ([Events that trigger workflows: schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule))

```yaml
on:
  schedule:
    - cron: "17 6 * * 1"   # 06:17 UTC, every Monday
```

A cron line has five fields, separated by spaces:

```text
minute  hour  day-of-month  month  day-of-week
17      6     *             *      1
```

You can use `*` for any value, `,` for a list, `-` for a range and `/` for a step. Day of week counts from 0 (Sunday), and the names `SUN` to `SAT` also work. The short macros such as `@daily` are not supported. Write all five fields.

Some rules to remember:

- **The time is UTC.** Each cron entry can also take a `timezone:` key with an IANA name such as `America/New_York`. If you leave it out, you get UTC. This lesson uses UTC only.
- **The shortest gap is 5 minutes.** GitHub does not run a schedule more often than that.
- **It runs on the default branch only.** The workflow file must exist there, and the run uses the latest commit there. A file that lives only on a feature branch never fires. That is why you merge first, then wait.
- **A run can be late.** When GitHub is busy, scheduled runs are delayed, and the start of every hour is one of the busy moments. Under heavy load some queued jobs may be dropped. So pick a minute that is not `0`. This repo uses `17`.

A missed run is a normal event, not a bug. Write the job so that skipping one night does no harm. For example, make it compare state ("what changed since last time?"), not count on being called exactly once per night.

One more detail. GitHub sends the notifications for a scheduled workflow to the person who last changed its `cron` line. ([Events that trigger workflows: schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule))

## When a schedule goes quiet

On a public repo, GitHub switches scheduled workflows off by itself when the repo has had no activity for 60 days. Nothing fails and nobody gets an error. The runs just stop appearing. The docs page links to a separate page on re-enabling. ([Events that trigger workflows: schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule))

You can look for a disabled workflow from the terminal. `gh workflow list` hides disabled workflows. Add `--all` to see them. Then turn the workflow back on:

```bash
gh workflow list --all
gh workflow enable nightly.yml
```

The Actions tab has the same switch: pick the workflow in the sidebar and use the enable button. The events page adds one more way. If someone with write access commits a change to the `cron` line of a deactivated scheduled workflow, the workflow comes back, and that person becomes its actor.

The sentence to keep: on a quiet public repo, a schedule is not forever. If a nightly job matters, put a check somewhere that tells you when it stops.

## Start a run by hand

The `workflow_dispatch` trigger adds a "Run workflow" button, and a command line way in. It is how you test a scheduled workflow without waiting for the clock. It can also take inputs. ([Events that trigger workflows: workflow_dispatch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch), [Triggering a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow))

```yaml
on:
  workflow_dispatch:
    inputs:
      note:
        description: "A short note to print in the log"
        required: false
        default: "run by hand"
        type: string
```

An input has a `type`: `string`, `boolean`, `choice`, `number` or `environment`. A workflow may have up to 25 inputs. Inside the workflow you read a value as `inputs.note`. ([Workflow syntax: workflow_dispatch inputs](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_dispatch))

Start a run with `gh workflow run`. Each `-f` sets one input:

```bash
gh workflow run nightly.yml -f note="trying it out"
gh run list --workflow nightly.yml --limit 3
gh run watch
```

Some things to know:

- **The file must be on the default branch** for the event to start a run. After the workflow has run once, you can point `--ref` at another branch or tag to test a change before you merge it.
- **`gh workflow run` only works for workflows with the trigger.** If the file has no `workflow_dispatch`, GitHub answers with an error. Observed on 2026-10-14: `gh workflow run ci.yml` against this repo, where `ci.yml` has no such trigger, answered `HTTP 422: Workflow does not have 'workflow_dispatch' trigger`.
- **Treat an input as untrusted text.** Pass it into a step with `env:`, as you did with secrets in GH5, and read it as `$NOTE`. Do not paste `${{ inputs.note }}` straight into a `run:` script.
- **A dispatch run always starts**, even when the event was made with the `GITHUB_TOKEN`. That is one of the exceptions listed in the section on pull requests opened by automation.

## Concurrency groups

By default, runs of one workflow can overlap. Two pushes a minute apart start two runs side by side. The `concurrency` key changes that. It puts a run (or a job) in a named group, and a group has at most one running member. ([Control the concurrency of workflows and jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency))

```yaml
concurrency:
  group: nightly
  cancel-in-progress: false
```

You can put it at the top of the workflow, or inside one job. The group name is any string or expression. Names are not case sensitive, and they are shared by every workflow in the repo. Two workflows that use the same name block each other, so pick a name that is only yours.

Here is what happens when a second run arrives while the first is still going:

- **The new run waits as `pending`.** It does not start yet.
- **A third run replaces the pending one.** By default only one run can wait. When a newer one arrives, GitHub cancels the older pending run. The running one is not touched.
- **`cancel-in-progress: true` also cancels the running one.** The newest run always wins. The value can be an expression.

There is a newer option for the case where you do not want to lose waiting runs. `queue: max` lets up to 100 runs wait in the group, and they start one by one, first in first out. A run that arrives when the queue is full is cancelled. The default is `queue: single`, which is the behaviour above. You cannot combine `queue: max` with `cancel-in-progress: true`. GitHub reports that as a workflow validation error. ([Control the concurrency of workflows and jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency), [Workflow syntax: concurrency](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency)) The docs describe `queue` as an optional property. Check that your own workflow passes validation before you rely on it.

Which setting should you choose?

- **Newest wins: `cancel-in-progress: true`.** Use it when an old run is useless once a newer one exists. A test run on a pull request is the classic case. A new push makes the old results stale.
- **Finish what you started: `cancel-in-progress: false`.** Use it when stopping half way does harm. A job that writes data or deploys should be left to end.
- **Keep every waiting run: `queue: max`.** Use it when each run has its own work to do and none may be skipped.

This repo's `ci.yml` shows the first case. Its group is built from the workflow name plus the pull request number (or the branch name for a push). The `cancel-in-progress` value is an expression: it is true for a pull request run and false otherwise. So a new push to a pull request cancels the old check, and a run on `main` is never cancelled.

## Pull requests opened by automation

In GH5 you learned that things done with the `GITHUB_TOKEN` do not start new workflow runs. That keeps one workflow from setting off another in a loop. GitHub changed one corner of that rule in 2026. ([Triggering a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow), [Events that trigger workflows: pull_request](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#pull_request))

Say a workflow creates or updates a pull request with the `GITHUB_TOKEN`. The `pull_request` event for `opened`, `synchronize` and `reopened` now creates the workflow runs, but they wait in an **approval required** state. The pull request shows a banner in the merge box. Someone with write access starts the runs with **Approve workflows to run**.

Keep the limits in view:

- Only those three `pull_request` actions are covered. Other actions, such as adding a label or closing, create no run.
- A push made with the `GITHUB_TOKEN` still starts no `push` workflow.
- `workflow_dispatch` and `repository_dispatch` events always create runs.
- A GitHub App token or a personal access token avoids the approval step: the `pull_request` workflows then run by themselves. The price is a bigger credential to store and guard (see GH5).

The project's research note says such pull requests used to get no run at all, and dates the change to the GitHub changelog entry of 2026-06-11. ([docs/research/github-plans-and-actions.md](https://github.com/siddharth-0044/hint-kata/blob/main/docs/research/github-plans-and-actions.md)) The practical rule: if automation opens pull requests in your repo, a person has to release the checks, or you must pay for a stronger token.

## The merge queue idea

Look at this problem. Two pull requests each pass CI on their own. Each one is fine against `main` as it was when CI ran. Then both merge, and together they break `main`. You can ask every author to update their branch and rerun CI before merging. On a busy repo that wastes a lot of time.

A merge queue solves it for you. Once a pull request passes the required checks, a user with write access adds it to the queue. The queue builds a temporary branch that holds the latest `main`, the changes of every pull request ahead of it, and this one. It runs the required checks on that branch. When they pass, it merges, in first in first out order. A pull request whose checks fail is removed from the queue, and the others carry on without it. ([Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue))

Two practical points from the docs:

- **Your CI must listen for the queue.** The queue sends a `merge_group` event, which is separate from `pull_request` and `push`. If a required check does not run on `merge_group`, the check never reports and the merge fails. A workflow that supports the queue lists both: `on: pull_request:` and `merge_group:`.
- **The queue has knobs.** The main ones are the merge method, how many checks may run at once, how many pull requests merge together, and how long the queue waits for CI.

Why can't this repo use one? Our repo belongs to a personal account. Observed on 2026-10-14: `gh api repos/siddharth-0044/hint-kata --jq .owner.type` prints `User`. The project's research note quotes the docs as saying that merge queues are for public repos owned by an organization, or for private repos of organizations on GitHub Enterprise Cloud. ([docs/research/github-plans-and-actions.md](https://github.com/siddharth-0044/hint-kata/blob/main/docs/research/github-plans-and-actions.md)) The cached copy of the page does not repeat that sentence, so check the current page and your plan before you plan around a queue.

What Hint Kata does instead is small. Its ruleset `protect-main` requires a pull request, squash merges and the `checks` status check. It does not require branches to be up to date. That is a trade: it keeps merges fast, and it accepts a small risk that two green pull requests clash. With one maintainer and a handful of pull requests a day, that risk is low. That is how the ruleset reads through `gh api` on 2026-10-14.

## How Hint Kata does it

Open `.github/workflows/docs-resync.yml` and `docs/runbooks/docs-resync.md`. Together they use every idea above. Read the file first, then the runbook.

**Triggers.** The workflow has three. A `schedule` of `17 6 * * 1` (Mondays, 06:17 UTC, off the hour on purpose). A `workflow_dispatch`, so the owner can run it by hand. And a `push` to `main` that touches `content/sources.yaml`.

**The `plan` job: a weekly pull request.** It runs for the schedule and the manual trigger, and only on `main`. It downloads every cached page again with `fetch_docs.py --update`, then writes a report of which sources changed and which lessons cite them. If any content hash changed, it opens or updates one pull request from the branch `docs-resync`, with the report as the body. If nothing changed, it opens nothing.

**Permissions and concurrency.** The top of the file says `contents: read`. The `plan` job replaces that with `contents: write` and `pull-requests: write`, because it must push a branch and open a pull request. No other job gets write access. The job sits in its own concurrency group, `docs-resync-plan`, with `cancel-in-progress: false`, so a run in progress is never cut off.

**The approval step.** The pull request is opened with the default `GITHUB_TOKEN`. So the `checks` workflow waits in the approval required state described above. The runbook tells the owner what to do: click **Approve workflows to run**, or push an empty commit from their own login, or close and reopen the pull request. The pull request body repeats the advice.

**The `embed` job: on merge.** When the plan pull request is merged, the merge is a push to `main` that touches `content/sources.yaml`. That starts `embed`. A small `gate` job first checks whether the two repository secrets exist, and prints only `true` or `false`. If they are missing, `embed` is skipped and the run stays green. Then `embed` compares the manifest before and after the push to find the source ids that changed.

**The one-id-per-call loop.** The fetch script's `--only` option accepts a single id. So the workflow loops in the shell and makes one call per changed id, for the fetch and again for the embed. The fetch loop looks like this:

```bash
read -ra ids <<< "$IDS"
for id in "${ids[@]}"; do uv run python scripts/fetch_docs.py --only "$id"; done
```

Only the embed step gets the secrets, through a step-level `env:`, as in GH5.

**A limit the runbook admits.** `embed` uses the group `docs-resync-embed` with `cancel-in-progress: false`. So runs queue and none is cancelled. But the default allows only one waiting run. If two merges land while one embed run is going, the older waiting run is replaced, and its ids can be skipped. The runbook's answer is to run the ingest script by hand for that id. The `queue: max` option from the concurrency section would keep every waiting run. The workflow does not use it today.

**The 60-day rule.** The repo is public, so its schedule can be switched off after 60 days without activity. The runbook shows the check (`gh workflow list --all`) and the fix (`gh workflow enable docs-resync.yml`).

Now build a small version yourself. The task page asks you to add `.github/workflows/nightly.yml` to your practice repo, run it by hand, and watch it. **Check my work** reads your workflow file and your run list.

Adapted from GitHub Docs, © GitHub, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Modified: summarized and adapted. Read 2026-10-14. Checked with `gh` 2.102. This site is not affiliated with GitHub.

**Sources:**
[Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows),
[Triggering a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow),
[Control the concurrency of workflows and jobs](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency),
[Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[Managing a merge queue](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue).

**Further reading (not used as a source):**
[Disabling and enabling a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows),
[Manually running a workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow),
[Approving workflow runs from forks](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks),
[Merging a pull request with a merge queue](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request-with-a-merge-queue).
