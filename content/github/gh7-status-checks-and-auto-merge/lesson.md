---
id: gh7-status-checks-and-auto-merge
track: github
title: "Status checks, required checks and auto-merge"
minutes: 30
pins:
  gh: "2.102"
sources:
  - github-pull-requests-reference-status-checks
  - github-pull-requests-troubleshooting-required-status-checks
  - github-pull-requests-how-tos-merge-and-close-pull-requests-automatically-merging-a-pull-request
  - github-repositories-configuring-branches-and-merges-in-your-repository-managing-rulesets-about-rulesets
  - github-repositories-configuring-branches-and-merges-in-your-repository-managing-rulesets-available-rules-for-rulesets
  - github-repositories-configuring-branches-and-merges-in-your-repository-managing-rulesets-creating-rulesets-for-a-repository
  - github-repositories-configuring-branches-and-merges-in-your-repository-managing-protected-branches-about-protected-branches
---
You open a pull request and the merge button is grey. The page says a check is "expected" or "waiting". What is a check, who sent it, and why can it block you? This lesson answers that. It then shows how to make a check required, how to watch it from the terminal, and how to let GitHub merge the pull request for you the moment everything is green. At the end you do all of it in your own practice repo. This site is not affiliated with GitHub. It teaches how GitHub works and links to the official pages.

One idea runs through the whole lesson. A required check is a name written in a rule. Almost everything that goes wrong is about that name, or about who is allowed to report it.

## What a status check is and who posts it

A status check is a result stuck to a commit. It says "this commit passed", "this commit failed" or "still testing". The pull request page reads the results on the latest commit and shows them in the merge box. ([Status checks](https://docs.github.com/en/pull-requests/reference/status-checks))

There are two kinds:

| Kind | What it carries | Who posts it |
|---|---|---|
| Check (a "check run") | Logs, test results, notes on lines of code | GitHub Apps, including GitHub Actions |
| Commit status | One simple state for the commit | Outside services and integrations |

GitHub Actions posts checks, never commit statuses. A rule can require either kind. If a check and a commit status share a name, both must pass. ([Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks))

Here are the check runs on this repo's `main` at the time of writing. The command is read-only, so you can run it yourself. The list changes over time, so yours may show more rows:

```bash
gh api repos/SiddharthMuramkar/hint-kata/commits/main/check-runs --jq '.check_runs[] | [.name, .app.slug, .conclusion] | @tsv'
```

```text
checks                           github-actions   success
update-pip-graph                 github-actions   success
Analyze (javascript-typescript)  github-actions   success
Analyze (python)                 github-actions   success
Analyze (actions)                github-actions   success
```

Each row has a name, the app that posted it, and a result. Three facts follow from it.

- **The name of an Actions check is the name of the job.** The job `name: checks` posts a check called `checks`.
- **Job names should be unique across all your workflows.** Two jobs with the same name make the result unclear, and that can block merging. ([About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches))
- **A finished check has a conclusion.** Three conclusions count as passing: `success`, `skipped` and `neutral`. Anything else, such as `failure`, `cancelled` or `timed_out`, does not.

Two more facts, and both matter later:

- **Anyone with write access can set the state of any status check.** They can do it through the API. So a name alone proves nothing about who sent it. That is why a rule can also name the app.
- **Only some events count.** A check from a workflow job is evaluated for a pull request only if the run came from `push`, `pull_request`, `pull_request_review`, `pull_request_target`, `deployment` or `deployment_status`. A run you start by hand with `workflow_dispatch` on the branch shows no check in the pull request and cannot satisfy a rule. ([Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks))

## Why a pull request waits

When a required check blocks you, the box usually says one of a few things. Match what you see to a cause before you change anything.

| You see | Why | What to do |
|---|---|---|
| **Waiting for status to be reported** | No check with the required name has been reported for this commit. The name in the rule does not match the job name (`Checks` is not `checks`), or the job was renamed, or the workflow never started. | Compare the two names letter by letter. Then open the Actions tab and look for a run. |
| A red `checks` | The job ran and failed. | Read the log (lesson GH2), push a fix. |
| Green on the old commit, pending on the new one | A required check must pass on the **latest** commit. Results from earlier commits do not count. | Wait for the new run. |
| *Required status check "build" was not set by the expected GitHub App* | Something other than the app named in the rule posted that name. | Look at who posted the check in the merge box. |

The first row hides a trap. A workflow can fail to start for several reasons: a `paths:` or `branches:` filter, a skip phrase in the commit message, or (lesson GH2) a merge conflict or a YAML error. When it does not start, its checks never appear. They stay pending, and the pull request is blocked. ([Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks))

Here is a workflow that does this to itself:

```yaml
name: ci
on:
  pull_request:
    paths:
      - "src/**"
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - run: echo "build the code"
```

A pull request that only edits `README.md` never starts this workflow. If `build` is a required check, that pull request waits forever. The docs give a short rule: do not require a workflow that can be skipped.

Skips come in three kinds, and they behave in three ways:

- **A whole workflow skipped** by a filter or a commit message. Its checks stay pending and block the merge.
- **One job skipped** by an `if:` condition. It reports `success` and does not block, even when it is required. A required check that an `if:` can switch off protects nothing while it is off.
- **A job that `needs` a failed job** is skipped too, and a skipped job may not block. For a required check that depends on other jobs, put `if: always()` next to `needs:`.

So the safe pattern is to let the workflow always start, and put any condition on a job inside it.

## Requiring checks with a ruleset

A check only blocks a merge when a rule says it must pass. In a ruleset, that rule is called `required_status_checks`. This is the one in this repo's ruleset, read from the API:

```json
{
  "type": "required_status_checks",
  "parameters": {
    "required_status_checks": [{ "context": "checks", "integration_id": 15368 }],
    "strict_required_status_checks_policy": false,
    "do_not_enforce_on_create": false
  }
}
```

- **`context`** is the check name. The match is exact.
- **`integration_id`** is the app that must post the check. `15368` is the GitHub Actions app. You can look it up with `gh api /apps/github-actions --jq .id`. The field is optional. If you leave it out, the rule accepts a check with that name from any source. With an app named, a check with the same name from another app is refused, so a person with write access cannot post a fake `checks` result. ([Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets))
- **`strict_required_status_checks_policy`** is the next section.
- **`do_not_enforce_on_create`** is an extra switch that this lesson leaves at `false`.

Three things about rulesets help here. ([About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets), [Creating rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository))

- **They stack.** If several rulesets target the same branch, GitHub adds all their rules together, and the most restrictive version of a rule wins. You can add a second ruleset without touching the first.
- **A ruleset exempts nobody by default.** Only the actors on its bypass list may skip it. An empty list, `"bypass_actors": []`, means the rule applies to you too.
- **`gh ruleset` can only read.** It has `list`, `view` and `check`. You create or change a ruleset with `gh api`, as you did in GH1 and GH2.

To see the rules that apply to a branch, use either of these:

```bash
gh ruleset check main                              # readable list
gh api repos/{owner}/{repo}/rules/branches/main    # JSON, all rulesets merged
```

## Strict and non-strict checks

The docs call the two modes "strict" and "loose". In the API it is the true or false value of `strict_required_status_checks_policy`. On the web form it is the box **Require branches to be up to date before merging**. ([Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets))

| | Strict (`true`) | Non-strict (`false`) |
|---|---|---|
| Rule | The branch must contain the latest `main` before it can merge. | The branch can merge even if `main` has moved on. |
| Cost | Every time another pull request merges, yours is behind. You update it and wait for CI again. | Fewer CI runs. |
| Risk | Little. What you tested is what lands. | Two pull requests that are green on their own can break each other once both are in. The docs warn that checks "may fail" after the merge. |

With strict mode, `gh pr merge` refuses a branch that is behind and says the head branch is not up to date with the base branch. Auto-merge waits too. You bring `main` in yourself. The docs say to merge or rebase the base branch into yours. `gh pr update-branch` does the merge, and `gh pr update-branch --rebase` does the rebase.

One note about the web form, from the [Creating rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository) page: if you select the up-to-date box, you must also define a check for the protection to take effect.

## Watching checks from the terminal

You do not need the browser to watch a pull request. These commands work on the pull request of the branch you are on:

```bash
gh pr checks                        # one line per check
gh pr checks --watch                # refresh until every check finishes
gh pr checks --watch --required     # watch only the checks that can block the merge
gh pr checks --watch --fail-fast    # stop at the first failure
```

`--required` matters because not every check is required. This is a real pull request from this repo, first with all checks and then with `--required`:

```text
$ gh pr checks
Analyze (actions)                pass   43s
Analyze (javascript-typescript)  pass   52s
Analyze (python)                 pass   51s
CodeQL                           pass   4s
checks                           pass   4m30s

$ gh pr checks --required
checks                           pass   4m30s
```

The exit code tells a script what happened: `0` when everything passed, `1` when a check failed, `8` while a check is still pending (the help text of `gh pr checks` lists the `8`). Two error messages are worth knowing. "no checks reported on the '<branch>' branch" means no run has posted anything yet, so wait a few seconds. "no required checks reported on the '<branch>' branch" means checks do exist, but none of them counts as required. The usual cause is the name mismatch from the section above: the name in the rule matches no check that was posted.

## Auto-merge

Auto-merge means: merge this pull request for me as soon as every rule is met. It removes the "wait, refresh, click" loop. ([Automatically merging a pull request](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/automatically-merging-a-pull-request))

**Three conditions.**

- The repository must allow it. Turn it on in the repo's settings, or run `gh repo edit --enable-auto-merge`. The API field is `allow_auto_merge`.
- You need write access to turn it on for a pull request.
- It is offered only on a pull request that cannot be merged yet, for example because a required check is still running.

**Turn it on for one pull request:**

```bash
gh pr merge --auto --squash
```

`gh` answers "will be automatically merged via squash when all requirements are met". You name the method because the ruleset allows only squash. If you try plain `gh pr merge --squash` on a blocked pull request, `gh` says it is not mergeable, because the base branch policy prohibits the merge, and suggests `--auto`.

**Timing.** In `gh` 2.102, `--auto` on a pull request that can already merge (`mergeStateStatus` is `CLEAN`, `HAS_HOOKS` or `UNSTABLE`) does not wait. It merges at once. This is in `gh`'s own source code, tag v2.102.0, in `pkg/cmd/pr/merge/merge.go`. So `--auto` means "merge now, or later when ready". To see the state of a pull request, run `gh pr view --json mergeStateStatus,autoMergeRequest`.

**When a check fails.** Nothing merges. Auto-merge stays armed and the pull request sits there, blocked. You push a fix, the checks run again on the new commit, and when they pass GitHub merges for you. The docs name only two things that switch auto-merge off: a push from someone without write access, and a change of the base branch. A red check is not one of them. To cancel it yourself, run `gh pr merge --disable-auto`.

**The branch is not deleted by `--delete-branch`.** `gh pr merge --help` says `--delete-branch` deletes "the local and remote branch after merge". But when auto-merge is armed, `gh` skips the deletion, local and remote, because the merge has not happened yet when the command ends. The flag does nothing. Use the repo setting instead. `gh repo edit --delete-branch-on-merge` makes GitHub delete the remote branch whenever any pull request merges. Your local copy stays. After you pull `main`, delete it with `git branch -D <name>`. Plain `-d` refuses, because a squash merge made a new commit and git cannot see that your branch was merged.

## How Hint Kata does it

This repo uses everything above. Open `.github/workflows/ci.yml`. It has one job, `checks`, and it runs on `pull_request` and on `push` to `main`. The facts below come from the live API, read-only, and from `docs/HARNESS.md`.

- **One ruleset, `protect-main`,** on the default branch, active, with an empty bypass list.
- **Its rules:** no deleting `main`, no force pushes, a pull request is required with 0 approvals and only squash allowed, and the check `checks` from the Actions app is required, non-strict.
- **Repo settings:** auto-merge is allowed, head branches are deleted on merge, and only squash merge is turned on.
- **The flow of a change:** push a branch, open the pull request, run `gh pr merge --auto --squash`, let `checks` run, and GitHub merges and deletes the branch. Nobody clicks merge. The agent allow-list in `docs/HARNESS.md` lets the builder run `gh pr merge --auto` but not `--admin`.
- **Only `checks` is required.** The CodeQL checks run on every pull request, as the `--required` example above shows, but they do not block.

**Why non-strict.** Several pull requests are often open at once. With strict mode, each merge would push every other pull request behind `main` and force a full CI run again. Non-strict skips that cost. The price is the small risk from the table above, and CI also runs on every push to `main`, so a bad mix shows up right after the merge. This is a trade-off, and a repo with many people merging at once may choose differently.

**Why an empty bypass list.** The agents here use the owner's token. Any bypass the owner has, they have. With none, the check cannot be skipped by mistake. If the rule ever has to be switched off in an emergency, the owner sets the ruleset's enforcement to `disabled`, fixes the problem, and sets it back to `active`.

Adapted from GitHub Docs, © GitHub, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Modified: summarized and adapted. Read 2026-10-14. Checked with `gh` 2.102. This site is not affiliated with GitHub.

**Sources:**
[Status checks](https://docs.github.com/en/pull-requests/reference/status-checks),
[Troubleshooting required status checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks),
[Automatically merging a pull request](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/automatically-merging-a-pull-request),
[About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets),
[Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets),
[Creating rulesets for a repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository),
[About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

**Further reading (not used as a source):**
[Managing auto-merge for pull requests in your repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-auto-merge-for-pull-requests-in-your-repository),
[`gh pr merge` manual](https://cli.github.com/manual/gh_pr_merge),
[`gh pr checks` manual](https://cli.github.com/manual/gh_pr_checks),
[`gh` source: `pr merge`](https://github.com/cli/cli/blob/v2.102.0/pkg/cmd/pr/merge/merge.go).
