---
id: gh8-rulesets-and-codeowners
track: github
title: "Rulesets, CODEOWNERS and required reviews"
minutes: 35
pins:
  gh: "2.102"
sources:
  - github-repositories-configuring-branches-and-merges-in-your-repository-managing-protected-branches-about-protected-branches
  - github-repositories-configuring-branches-and-merges-in-your-repository-managing-rulesets-about-rulesets
  - github-repositories-configuring-branches-and-merges-in-your-repository-managing-rulesets-creating-rulesets-for-a-repository
  - github-repositories-configuring-branches-and-merges-in-your-repository-managing-rulesets-available-rules-for-rulesets
  - github-repositories-managing-your-repositorys-settings-and-features-customizing-your-repository-about-code-owners
  - github-pull-requests-how-tos-review-pull-requests-approving-a-pull-request-with-required-reviews
---
A good habit is only a habit until the repository enforces it. In GH1 you made a ruleset that stops direct pushes to `main`. In GH2 you made `checks` a required check. This lesson fills in the rest: how rulesets differ from the older branch protection, which rules matter, who may skip them, why a one-person repo cannot require approvals, and how a `CODEOWNERS` file asks the right person to review. You then read the real ruleset of this repo and build a stricter one in your practice repo. This site is not affiliated with GitHub. It teaches how GitHub works and links to the official pages.

One idea runs through it all: a rule on GitHub only protects you if GitHub enforces it. A note in a README does not.

## Branch protection rules and rulesets

GitHub has two tools for protecting a branch. Both are described in [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) and [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets).

- **A branch protection rule** is the older tool. It matches a branch name or a name pattern and holds a set of settings. Only one branch protection rule applies to a branch at a time. By default it also blocks force pushes and deletions, and by default it does not apply to people with admin permission, unless you turn on "Do not allow bypassing the above settings".
- **A ruleset** is a named list of rules. Many rulesets can apply to the same branch at once. A ruleset has no priority number. GitHub adds the rules up, and where two rulesets set the same rule differently, the strictest version wins. You can switch a ruleset between **Active** and **Disabled** without deleting it. Anyone with read access to the repo can see its active rulesets. A ruleset also has a bypass list (see below).

The two tools also layer with each other. If a ruleset and a branch protection rule target the same branch, all of it applies. An example from the docs: a ruleset asks for three reviews and a rule asks for two. The branch needs three.

Both tools can match many branches with a name pattern. The pattern syntax is `fnmatch`. A `*` does not match a `/`, so `qa/*` matches `qa/login` but not `qa/login/fix`. Use `qa/**/*` to match any depth. A ruleset can also list branches to include and branches to exclude. ([Creating rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository))

This course teaches rulesets. GitHub's own code owners page lists rulesets as an alternative to branch protection with some advantages, such as statuses, easier discovery without admin access, and applying several at once. The Hint Kata repo uses one ruleset, called `protect-main`. Rulesets worked in the public repos used in these lessons. The pinned pages give no table of which plans can use them. If you use a private repo, check GitHub's plans page before you rely on one.

## The rules that matter

A ruleset is a list of rules. In the web form each rule has a title. In the API each rule has a `type`. You need both names, because `gh ruleset check` prints the API names. The rules are described in [Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).

| In the form | API `type` | What it does |
| --- | --- | --- |
| Require a pull request before merging | `pull_request` | Every change must come through a PR. The PR needs no approval unless you set a number. |
| Require status checks to pass | `required_status_checks` | The named checks must pass before the merge (see GH2). |
| Block force pushes | `non_fast_forward` | Nobody can rewrite the branch history. |
| Restrict deletions | `deletion` | Only people on the bypass list can delete the branch. |
| Require linear history | `required_linear_history` | No merge commits. A PR must be squashed or rebased. |
| Require signed commits | `required_signatures` | Only signed and verified commits can arrive. |

The form shows "Block force pushes" and "Restrict deletions" ticked by default. The names in the API come from the REST page [Create a repository ruleset](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset), which this lesson uses as further reading.

The `pull_request` rule has the most settings. These are the ones that matter:

- **Required approvals.** How many approving reviews the PR needs. Zero means "a PR must exist, but nobody has to approve it".
- **Dismiss stale approvals.** If someone pushes new commits that change the diff, earlier approvals are thrown away. The PR needs a fresh approval. This stops a bait and switch: get an approval, then push something else.
- **Require review from code owners.** A PR that changes a file with a code owner needs an approval from that owner. You will meet this again below.
- **Require approval of the latest push.** The newest push needs an approval from someone who did not make it.
- **Require conversation resolution.** Every review thread must be resolved before the merge (see GH3).
- **Allowed merge methods.** Merge, squash, rebase, or a subset. This repo allows squash only.

Two details cause surprises:

- **Linear history needs a merge method that makes it.** The repo must allow squash or rebase merging first, because a plain merge commit is exactly what the rule forbids.
- **Strict or loose checks.** With "Require branches to be up to date before merging" on, a PR must contain the latest `main` before it merges. It means more re-runs. GH1 covers this.

## Bypass actors and why this repo has none

A ruleset can have a bypass list. It names who may skip the rules. The docs list what you can add: repository admins, the maintain or write roles, teams, GitHub Apps, and Dependabot. You can also pick **For pull requests only**. That actor must still open a PR, but may merge it without meeting the rules. This leaves a trail in the PR. ([Creating rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository))

A bypass is an exit door. It is sometimes needed. It also means the rules are not rules for that actor.

The Hint Kata ruleset has no bypass actors. You can see it yourself, because `gh ruleset view` prints it:

```bash
gh ruleset view 25079334 -R SiddharthMuramkar/hint-kata
```

At the time of writing, the output contains `You can bypass: never` and `This ruleset cannot be bypassed`. Here is why that is the right choice for this repo:

1. **The owner and the agents share one admin token.** The agents in `docs/HARNESS.md` run with the owner's rights. If the owner could bypass, so could a mistaken agent command. The ruleset is "the real lock on `main`", as that file puts it. The agents' permission list also denies `gh api -X PUT`, `-X PATCH` and `-X DELETE`, which makes it harder for an agent to loosen a ruleset by accident.
2. **It costs nothing.** The ruleset asks for zero approvals, so the owner never needs a bypass to get a PR merged. The rules only ask for a PR and a passing `checks` job.
3. **The emergency exit is deliberate.** If CI itself breaks, the owner can set the ruleset to **Disabled** in Settings, fix the problem, and switch it back. That is a visible, slow action, not a standing permission.

## The self-approval limit

[Approving a pull request with required reviews](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews) states a short rule: pull request authors cannot approve their own pull requests.

Now think about a repo with one human. You open every PR, so you are the author of every PR. If the ruleset asks for **1** approval and has no bypass list, nobody can give it. The merge box says a review is required, and you have no way to provide one. Your options:

- **Add a second person** with write access. They approve, and you merge.
- **Put yourself on the bypass list.** Now the approval rule does not bind you. You have switched your own rule off.
- **Ask for zero approvals,** and put the weight on other gates.

Hint Kata takes the third option. Look at what it does enforce, and what it leaves to a person:

| Layer | Who runs it | Does GitHub enforce it? |
| --- | --- | --- |
| A PR must exist (`pull_request`) | GitHub | Yes |
| The `checks` job must pass (`required_status_checks`) | GitHub Actions | Yes |
| No force push, no deletion | GitHub | Yes |
| A reviewer agent reads the diff | `diff-reviewer`, see `docs/HARNESS.md` | No |
| The owner reads the PR and decides | A person | No |

The reviewer agent returns a list of findings. A person then decides what to do. This is a real review habit, but GitHub cannot see it, so GitHub cannot demand it. The docs add one more warning: approvals by GitHub Copilot appear in the reviewers list, but they do not count toward the merge requirements. An automatic reviewer is advice, not a gate.

When a second person joins, raise the count to **1** and turn on the code-owner rule (next section). Until then, zero approvals plus required checks is the honest setting.

Zero approvals also explains a line in the `gh ruleset check` output: `require_extra_approval_for_unattributed_changes`. The form calls it "Require an additional approval for unattributed Copilot pull requests". The docs say it does nothing when the ruleset asks for zero approvals.

## CODEOWNERS

A `CODEOWNERS` file says who is responsible for which files. When a PR changes a file that has an owner, GitHub asks that owner for a review. ([About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners))

**Where it lives.** Put a file called `CODEOWNERS` in `.github/`, in the repo root, or in `docs/`. If more than one exists, GitHub looks in that order and uses the first one it finds. The file belongs to a branch. GitHub reads the version on the **base branch** of the PR, the branch the PR merges into. A `CODEOWNERS` file that is only in your PR's own branch does nothing for that PR. Merge the file first, then open the PR that needs it.

**The syntax.** Each line is a pattern, then one or more owners. An owner is `@username`, `@org/team`, or an email address of an account. A `#` starts a comment. The patterns follow most gitignore rules. The ones you will use:

```text
# Last matching line wins.
*            @your-user            # everything
*.yml        @your-user            # any .yml file, in any folder
/docs/       @your-user            # the docs folder at the root, and everything below it
docs/*       @your-user            # files directly in docs, but not in docs/guide/
/.github/CODEOWNERS  @your-user    # one exact file
```

Rules to remember:

- **The last matching line wins.** Put the general line first and the special lines after it.
- **Several owners go on one line.** Put them all on the same line. If you put them on separate lines, only the last one counts.
- **Any one owner is enough** when a review from a code owner is required. Two owners on one line do not both have to approve.
- **Paths are case sensitive,** even on a Mac. `*.yml` does not match a `.yaml` file.
- **Some gitignore tricks do not work.** You cannot negate with `!`. You cannot use `[ ]` ranges. You cannot escape a leading `#`.
- **A bad line is skipped,** and the rest of the file still works. The same is true for an owner that does not exist or has no write access: no owner is assigned.
- **Owners need write access** to the repo. A team must have write access too.
- **Drafts are skipped.** Owners are not requested while a PR is a draft. They are notified when you mark it ready.
- **The file must be under 3 MB.**

**A request is not a requirement.** On its own, `CODEOWNERS` only asks. The PR can still merge without the owner's approval. To make the approval a gate, turn on code owner review in the rule: **Require review from Code Owners** in a branch protection rule, or `require_code_owner_review: true` in the `pull_request` rule of a ruleset. Even then, an approval from any one owner is enough.

To protect the file itself, give it an owner as well, for example `/.github/CODEOWNERS @your-user`. If nobody owns it, a PR that edits it needs no owner's approval, so someone could take your name out.

Remember the self-approval limit: if you are the only owner and you wrote the PR, a required code owner review can never be met. In your practice repo, you will add the file but leave the requirement off.

## Reading rules with gh

The `gh ruleset` commands only read. They never change anything. (`gh ruleset --help`)

| Command | What it shows |
| --- | --- |
| `gh ruleset list` | The rulesets of the repo, with id, name, source, status and the number of rules. |
| `gh ruleset view <id>` | One ruleset: enforcement, bypass list, conditions and rules. |
| `gh ruleset check <branch>` | Every rule that applies to that branch, and which ruleset it comes from. The branch does not have to exist. |

Add `-R owner/repo` to look at another repo. Try them on this one:

```bash
gh ruleset list -R SiddharthMuramkar/hint-kata
gh ruleset check main -R SiddharthMuramkar/hint-kata
```

At the time of writing, `check` lists four rules for `main`, all from `protect-main`:

- `deletion`
- `non_fast_forward`
- `pull_request`, with `required_approving_review_count: 0`, `require_code_owner_review: false` and `allowed_merge_methods: [squash]`
- `required_status_checks`, with the context `checks`

Read it against this lesson. The branch cannot be deleted or force-pushed. A PR is required but needs no approval. Only squash merges are allowed. The job `checks` must pass. The code-owner switch is off, and this repo has no `CODEOWNERS` file yet.

The same rules are available as JSON from the API. Checks in this course use that form, because `jq` can test it:

```bash
gh api repos/SiddharthMuramkar/hint-kata/rules/branches/main --jq '[.[].type]'
```

This prints a list of the rule types, for example `["deletion","non_fast_forward","pull_request","required_status_checks"]`. There is no `CODEOWNERS` file in `.github/` when `gh api repos/OWNER/REPO/contents/.github/CODEOWNERS` answers `Not Found`.

## Creating a ruleset with gh api

`gh ruleset` cannot create anything. To create a ruleset you send JSON to the API with `gh api`. Save the JSON below in a file called `main-guard.json`. Put the file somewhere outside your repo folder, so you do not commit it by accident.

```json
{
  "name": "main-guard",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] }
  },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [{ "context": "checks", "integration_id": 15368 }]
      }
    }
  ]
}
```

Then, from inside your practice repo folder, send it:

```bash
gh api --method POST repos/{owner}/{repo}/rulesets --input main-guard.json
```

gh fills in `{owner}` and `{repo}` from the repo in the current folder. It prints the new ruleset, with its `id`.

Read the JSON piece by piece:

- `"enforcement": "active"` means it takes effect at once. `"disabled"` would store it without enforcing it.
- `"bypass_actors": []` is an empty bypass list. Nobody may skip these rules, not even you.
- `"~DEFAULT_BRANCH"` is a special value for "whatever the default branch is". The Hint Kata ruleset uses it too.
- `deletion` and `non_fast_forward` need no settings.
- The `pull_request` rule must list its settings. Zero approvals, and the code-owner requirement off.
- `required_status_checks` names the job `checks` from GH2. The `integration_id` 15368 means "only the GitHub Actions app may report this check".

This shape is the same one the API gives back for a ruleset. You can see it for the real `protect-main` with `gh api repos/SiddharthMuramkar/hint-kata/rulesets/25079334`. Every key in the JSON above appears there, with the same kind of value. So one habit is to read a working ruleset first and copy its shape.

If your practice repo already has the GH1 ruleset, you now have two rulesets on `main`. That is allowed. Run `gh ruleset check main` and you will see rules listed once for each ruleset. The strictest version of each rule applies.

Now try it. The task page walks you through a `CODEOWNERS` file, the `main-guard` ruleset and a PR that touches a `.yml` file.

Adapted from GitHub Docs, © GitHub, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Modified: summarized and adapted. Read 2026-10-14. Checked with `gh` 2.102. This site is not affiliated with GitHub.

**Sources:**
[About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches),
[About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets),
[Creating rulesets for a repository](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository),
[Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets),
[About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners),
[Approving a pull request with required reviews](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews).

**Further reading (not used as a source):**
[REST API: Create a repository ruleset](https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset),
[REST API: List CODEOWNERS errors](https://docs.github.com/en/rest/repos/repos#list-codeowners-errors).
