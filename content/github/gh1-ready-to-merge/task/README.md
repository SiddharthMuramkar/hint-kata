# Task: protect main in a practice repo

You will make a small public practice repo, open a pull request, add a ruleset that requires pull requests, and then watch GitHub refuse a direct push to `main`.

Use a **public** repo. Rulesets are free on public repos. On a private repo they need a paid plan.

You need the GitHub CLI (`gh`, version 2.102 or newer) and `git`. Open the integrated terminal in VS Code (**Terminal > New Terminal**, or Ctrl+`). Check that you are logged in:

```bash
gh auth status
```

## 1. Create the practice repo

Pick a name, for example `hint-kata-practice`. The `--add-readme` flag gives `main` a first commit, so a pull request has something to compare to.

```bash
gh repo create hint-kata-practice --public --add-readme --clone
cd hint-kata-practice
```

Find the full name of the repo. It looks like `your-user/hint-kata-practice`:

```bash
gh repo view --json nameWithOwner --jq .nameWithOwner
```

Open the `.env` file at the root of the Hint Kata project and add that name. The site reads it when you press "Check my work". Never put a token in this file.

```text
PRACTICE_REPO=your-user/hint-kata-practice
```

## 2. Branch, commit and open a pull request

```bash
git switch -c add-notes
echo "Notes for my practice repo" > NOTES.md
git add NOTES.md
git commit -m "Add a notes file"
git push -u origin add-notes
gh pr create --fill
```

`gh pr create --fill` takes the title and body from your commit. It prints the PR address. Open it in the browser and look at the five parts: conversation, commits, checks, files changed and the merge box.

Do not merge yet.

## 3. Add a ruleset to main

A ruleset is created through the API, because `gh ruleset` can only read. The command below sends JSON on standard input (`--input -`). The `{owner}` and `{repo}` words are filled in by `gh`, because you are inside the cloned repo.

The ruleset does three things on the default branch:

- `pull_request` requires changes to arrive through a PR, with **0** approvals (you cannot approve your own PR).
- `non_fast_forward` blocks force pushes.
- It has no bypass list, so it applies to you too.

```bash
gh api -X POST repos/{owner}/{repo}/rulesets --input - <<'EOF'
{
  "name": "protect-main",
  "target": "branch",
  "enforcement": "active",
  "conditions": {
    "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] }
  },
  "rules": [
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
    }
  ]
}
EOF
```

See what applies to `main`:

```bash
gh ruleset check main
```

You should see `non_fast_forward` and `pull_request` in the list.

## 4. Try to push straight to main

Make a commit on `main` and push it:

```bash
git switch main
echo "sneaky change" >> README.md
git commit -am "Change main directly"
git push origin main
```

The push is rejected. The message mentions `Repository rule violations` and that changes must be made through a pull request. That refusal is the ruleset doing its job.

Undo the local commit so your copy matches the server again:

```bash
git reset --hard origin/main
```

Now merge the real pull request the way the rule wants, and delete the branch:

```bash
gh pr merge add-notes --squash --delete-branch
```

## 5. Check my work

Press **Check my work** on the lesson page. The site runs read-only `gh` commands against your practice repo and shows one line per check:

1. A pull request exists from a branch that is not `main`.
2. The repo has at least one ruleset.
3. The rules on `main` include `pull_request`.
4. The rules on `main` include `non_fast_forward`.

If a check fails, the line shows what `gh` printed. The most common cause is a wrong `PRACTICE_REPO` value in `.env`.
