# Task: add CI to your practice repo

You will add a workflow with one job named `checks`, watch it run on a pull request, merge it, and then make `checks` a required status check in your ruleset on `main`.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. It is a public repo with a ruleset on `main`. If you do not have one yet, stop here and do the setup in lesson GH1 first. The checker below needs it.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code.

## 1. Open the repo and make a branch

1. In VS Code, choose **File > Open Folder** and open your practice repo folder.
2. Open the terminal with **View > Terminal**.
3. Run:

```bash
git switch main
git pull
git switch -c add-ci
```

## 2. Create the workflow file

1. In the Explorer, create the file `.github/workflows/ci.yml`. VS Code makes the folders for you when you type the whole path in the new-file box.
2. Paste this into it:

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
jobs:
  checks:
    name: checks
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - run: python3 -c "print('ok')"
```

Three things to notice. The job id and its `name:` are both `checks`. The checkout action is pinned to a SHA, with the version in a comment. The `permissions` block gives the token read access only.

## 3. Open a pull request and watch it

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add checks workflow"
git push -u origin add-ci
gh pr create --fill
gh pr checks --watch
```

Wait until `checks` shows a pass. If it fails, run `gh run list --limit 3`, then `gh run view <run-id> --log-failed`, and read what it says.

When it is green, merge the pull request. Your GH1 ruleset allows squash merges:

```bash
gh pr merge --squash --delete-branch
git switch main
git pull
```

## 4. Make `checks` a required check

The ruleset update replaces the whole list of rules, so read the ruleset first and send it back with one rule added.

1. Find the id of the ruleset that applies to `main`:

```bash
gh ruleset list
```

2. Set `ID` to that number, and run this from inside your practice repo folder. It reads the ruleset, adds a `required_status_checks` rule for the context `checks` from the GitHub Actions app (id 15368), and sends it back with `PUT`:

```bash
ID=<the id from the list>
gh api repos/{owner}/{repo}/rulesets/$ID \
  --jq '{name, target, enforcement, bypass_actors, conditions,
         rules: (.rules | map(select(.type != "required_status_checks")) + [
           {type: "required_status_checks", parameters: {
             strict_required_status_checks_policy: false,
             do_not_enforce_on_create: false,
             required_status_checks: [{context: "checks", integration_id: 15368}]}}])}' \
  | gh api -X PUT repos/{owner}/{repo}/rulesets/$ID --input -
```

If you already had a required status checks rule with other checks, add those to the `required_status_checks` list too, because this command replaces that rule.

3. Check that GitHub applies it:

```bash
gh ruleset check main
```

You should see a `required_status_checks` rule that lists the context `checks`.

## 5. Optional: break it on purpose

Make a new branch and rename the job to `ci` (keep the rest). Open a pull request. You should see "Waiting for status to be reported", because no check called `checks` is reported. Put the name back, or close the pull request. Then break a step on purpose, for example `python3 -c "raise SystemExit(1)"`, and read the failure with `gh run view --log-failed`.

## Check my work

Set `PRACTICE_REPO` in `.env`, then press **Check my work**. It runs read-only `gh` calls:

- A workflow file exists in `.github/workflows` on the default branch.
- A workflow run exists for a pull request.
- `checks` is a required status check on `main`.
