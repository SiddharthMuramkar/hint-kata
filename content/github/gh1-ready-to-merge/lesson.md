---
id: gh1-ready-to-merge
track: github
title: "Is this PR ready to merge?"
minutes: 30
pins:
  gh: "2.102"
sources:
  - github-get-started-using-github-github-flow
  - github-pull-requests-get-started-about-pull-requests
  - github-pull-requests-reference-pull-request-reviews
  - github-pull-requests-reference-status-checks
  - github-pull-requests-reference-pull-request-merges
  - github-pull-requests-how-tos-review-pull-requests-approving-a-pull-request-with-required-reviews
  - github-repositories-configuring-branches-and-merges-in-your-repository-managing-rulesets-about-rulesets
  - github-repositories-configuring-branches-and-merges-in-your-repository-managing-rulesets-available-rules-for-rulesets
---
Every change to a shared project ends with one question: is it safe to merge? A green tick is not the whole answer. In this lesson you learn the signals that make up a good answer, and how a repository can enforce some of them for you. This site is not affiliated with GitHub. It teaches how GitHub works and links to the official pages.

## GitHub flow in one picture

GitHub flow is a small, branch-based way to work. It has six moves. Each one has a reason. See [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow).

```text
main ──────────────────────────────●──────▶  (the branch everyone trusts)
       \                          /
        └─ branch ─ commits ─ PR ─ review ─ checks ─ merge
```

1. **Branch.** Make a branch with a short, clear name. It is a safe place to work. Nothing reaches `main` until you merge.
2. **Commits.** Save your work in small steps, each with a clear message. Push them, so your work is backed up and others can see it.
3. **Pull request (PR).** Ask for the branch to be merged into `main`. Write what changed and why.
4. **Review.** Other people read the change, ask questions and suggest edits. You push more commits and the PR updates by itself.
5. **Checks.** Automated jobs, such as tests, run on the PR. You see the results next to the review.
6. **Merge.** When the work is approved and the checks pass, you merge it. Then you delete the branch.

The order matters. You open the PR before the review, so that the review and the checks both see the same diff. You merge last, after the evidence is in.

### What a pull request really is

A PR is a conversation about a diff. It proposes merging one branch into another. It gives people one place to talk about the change, line by line, before it becomes part of the project. See [About pull requests](https://docs.github.com/en/pull-requests/get-started/about-pull-requests).

A PR page has five parts:

- **Conversation:** the description, comments, reviews and a timeline.
- **Commits:** how the branch changed over time.
- **Checks:** the results of the automated jobs.
- **Files changed:** the diff that reviewers comment on.
- **Merge box:** a summary of what must still happen before you can merge.

A PR can be a **draft**. A draft says "I want early feedback, but this is not ready." You can open one with `gh pr create --draft` and later mark it ready with `gh pr ready`. A draft is never ready to merge, whatever else is green.

## Reviews

A review has three possible decisions. See [Pull request reviews](https://docs.github.com/en/pull-requests/reference/pull-request-reviews).

| Decision | What the reviewer is saying |
| --- | --- |
| Comment | "Here is some feedback." It does not approve and it does not block. |
| Approve | "This looks ready to merge." |
| Request changes | "Please fix this before merging." |

By default, **Request changes** is only a signal. It becomes a real block when the repository requires a pull request through a ruleset or branch protection. Then the reviewer who asked for changes must approve later, or someone with write access must dismiss that review. See [Approving a pull request with required reviews](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews).

Two more facts from that page:

- **You cannot approve your own PR.** The author is never a valid approver.
- Repository owners and admins can still merge a PR that has no approval.

What does this mean if you work alone? A rule that needs one approval would lock you out, because you are the only person who could review. So solo developers usually require a pull request but set the number of approvals to **zero**. You lose the second pair of eyes, but you keep the PR, the checks and the history. Later in this lesson you set up exactly this.

Comments can also be left on single lines. Some repositories can require that every such thread is resolved before the merge. An open thread is an open question. Treat it as a blocker until someone answers it.

## Status checks

A status check tells you whether a commit meets a condition, such as "the tests pass". Most checks come from automation, for example GitHub Actions. See [Status checks](https://docs.github.com/en/pull-requests/reference/status-checks).

A check has a state while it runs (queued, in progress) and a conclusion when it ends (success, failure, cancelled, timed out and a few more). Two conclusions surprise people. **Neutral** and **skipped** both count as a success.

You can mark some checks as **required**. A required check must pass before the PR can merge. A check that is not required is only advice.

Two things to know about required checks:

- **"Waiting for status to be reported."** The ruleset names a check, but no job with that name has reported. Often the workflow never started on this PR, or the job was renamed. The check is not failing. It is missing, and a missing required check blocks the merge just the same.
- **Strict or non-strict.** With a **strict** rule, the branch must be up to date with `main` before merging. If `main` moved, you must update the branch and wait for the checks again. With a **non-strict** (also called loose) rule, you can merge an older branch. That saves builds, but the checks may fail after the merge, because they never ran on the combined code. See [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

From the terminal, `gh pr checks <number>` lists the checks for a PR. Add `--required` to see only the required ones.

## Merge methods

When you merge, you pick how the commits land on the base branch. See [Pull request merges](https://docs.github.com/en/pull-requests/reference/pull-request-merges).

| Method | Result on `main` | Good when |
| --- | --- | --- |
| Merge commit | Keeps every commit and adds one merge commit. | Every commit tells its own story. |
| Squash and merge | All commits become one commit. | The PR is one logical change, with small fix-up commits. |
| Rebase and merge | Each commit is replayed on top of `main`, with no merge commit. | The commits are already tidy and you want a straight line. |

**This repo squashes.** Each PR becomes one commit on `main`, and its title becomes the commit message. The history reads like a list of finished changes. The noisy "fix typo" commits stay in the PR, where they are still visible, but they do not clutter `main`. The price: the small commits are not kept as separate commits on `main`. Squashing also works best for short-lived branches. If you keep working on a branch after a squash merge, the next PR can show old commits again and cause repeat conflicts.

With the CLI: `gh pr merge --squash`.

## Rulesets and branch protection

Everything so far is a habit unless the repository enforces it. Two tools do that. See [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets).

- **Classic branch protection** is the older tool. One rule applies to a branch pattern.
- **Rulesets** are the newer one, and the one we teach. A ruleset is a named list of rules. Several rulesets can apply to the same branch, and they add up (the strictest version of each rule wins). You can switch one between active and disabled without deleting it. Anyone with read access can see the active rules.

Rulesets and branch protection work together. If both exist, all rules apply. On a **public** repository, both are free. On a private repository you need a paid plan.

Three rules do most of the work for a small project. Each is described in [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

- **Require a pull request before merging.** All changes to the branch must come through a PR. The PR does not need an approval, unless you also set a number of approvals.
- **Require status checks to pass.** The named checks must pass before the merge.
- **Block force pushes.** Nobody can rewrite the branch history. This rule is named `non_fast_forward` in the API.

What happens when you break a rule? Suppose `main` requires a PR and you run `git push origin main`. Git sends your commits, and GitHub refuses them. You see a message that starts like `remote: error: GH013: Repository rule violations found for refs/heads/main`, followed by a line such as "Changes must be made through a pull request". Nothing on the server changes. You fix it by moving the commit to a branch and opening a PR.

To see which rules apply to a branch, run `gh ruleset check main`. It lists each rule and the ruleset that sets it. (`gh ruleset` can only read. To create a ruleset you use `gh api`, as in the task below.)

## The ready-to-merge checklist

Put it all together. Before you merge, look for these six signals:

1. **It is not a draft.** The PR is marked ready for review.
2. **Required checks are green.** None is failing, missing or still running. Open a failing check before you decide anything.
3. **Review is settled.** There is no "request changes" left open, and the approvals the repo requires are present.
4. **No open threads.** Every review comment has an answer or a fix.
5. **The branch is current.** There are no conflicts. If the rule is strict, the branch is up to date with `main`.
6. **You know what it changes.** The diff matches the description, and nothing surprising is in it, such as a secret, a deleted test or a file in a sensitive area.

Signals 1 to 5 are things the repository can tell you. `gh pr view <number> --json isDraft,reviewDecision,mergeStateStatus` shows several of them at once. Signal 6 is yours. Automation cannot judge it for you. That is why a green check alone never means "ready".

## Watch it run

Now watch a real PR. The player below replays pull request number 23 from the repo that builds this site. It has two commits, a set of checks, and a squash merge. At the end you decide whether the PR was ready to merge, and the player tells you what the evidence was. Notice what is missing from the evidence: nobody reviewed this PR. The repo's ruleset requires a PR and green checks but zero approvals, because the author is also the only maintainer.

**Sources:**
[GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow),
[About pull requests](https://docs.github.com/en/pull-requests/get-started/about-pull-requests),
[Pull request reviews](https://docs.github.com/en/pull-requests/reference/pull-request-reviews),
[Status checks](https://docs.github.com/en/pull-requests/reference/status-checks),
[Pull request merges](https://docs.github.com/en/pull-requests/reference/pull-request-merges),
[Approving a pull request with required reviews](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews),
[About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets),
[Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).
Adapted from GitHub Docs, © GitHub, CC BY 4.0. Modified: summarized and adapted. Checked with `gh` 2.102.
