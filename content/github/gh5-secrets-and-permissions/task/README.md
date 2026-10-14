# Task: guard a secret in your practice repo

You will add a workflow whose token can only read, create an environment called `practice` with one secret, and run a job that uses that secret and prints only its length.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. It is a public repo. Environments need a public repo on a free GitHub account. If you do not have the practice repo yet, stop here and do the setup in lesson GH1 first. The checker below needs it.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code.

**Secret rule. Never paste a secret value into chat, into a file, or into a pull request.** You type the value in only two places: the GitHub web form, or the hidden prompt of `gh secret set`. Use a made-up practice value, such as three random words. Do not use a real password or a real API key. The logs of a public repo are public.

## 1. Open the repo and make a branch

1. In VS Code, choose **File > Open Folder** and open your practice repo folder.
2. Open the terminal with **View > Terminal**.
3. Run:

```bash
git switch main
git pull
git switch -c add-secrets-practice
```

## 2. Create the environment and its secret

1. Open your repo on GitHub: run `gh repo view --web`.
2. Click **Settings**, then **Environments** in the left sidebar, then **New environment**.
3. Name it exactly `practice`, in lower case, then click **Configure environment**.
4. Leave the protection rules empty. You are the only person in this repo, so a required reviewer would only be you.
5. Back in the VS Code terminal, add the secret:

```bash
gh secret set PRACTICE_TOKEN --env practice
```

6. At the prompt, type your made-up value and press Enter. The terminal hides what you type.
7. Check that the secret exists. The list shows names and dates, never values:

```bash
gh secret list --env practice
```

## 3. Create the workflow file

1. In the Explorer, create the file `.github/workflows/secrets-practice.yml`. VS Code makes the folders for you when you type the whole path in the new-file box.
2. Paste this into it:

```yaml
name: Secrets practice
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  show-length:
    name: show length
    runs-on: ubuntu-latest
    timeout-minutes: 5
    environment: practice
    steps:
      - name: Print the length of the secret
        env:
          PRACTICE_TOKEN: ${{ secrets.PRACTICE_TOKEN }}
        run: |
          echo "PRACTICE_TOKEN has ${#PRACTICE_TOKEN} characters"
```

Four things to notice:

- The top-level `permissions:` block lists one line, `contents: read`. Everything else becomes `none`.
- The job names `environment: practice`. That is what lets it read the environment's secret.
- The secret goes in through `env:` on the one step that needs it.
- The step prints the length with `${#PRACTICE_TOKEN}`. It never prints the value. There is no checkout step, because this job reads no files.

## 4. Open a pull request and merge it

```bash
git add .github/workflows/secrets-practice.yml
git commit -m "ci: add secrets practice workflow"
git push -u origin add-secrets-practice
gh pr create --fill
```

If you did GH2, your `checks` workflow runs on this pull request. Wait for it with `gh pr checks --watch`. Then merge. Your GH1 ruleset allows squash merges:

```bash
gh pr merge --squash --delete-branch
git switch main
git pull
```

## 5. Run it and read the log

A `workflow_dispatch` workflow can only be started once its file is on the default branch. That is why you merged first.

```bash
gh workflow run secrets-practice.yml
sleep 5
gh run list --workflow secrets-practice.yml --limit 1
```

Copy the run id from the list. Then:

```bash
gh run watch <run-id>
gh run view <run-id> --log
```

In the log, find the line `PRACTICE_TOKEN has N characters`. `N` is the length of the made-up value you typed. If it says `0`, the secret did not reach the job. Check that the secret name is exactly `PRACTICE_TOKEN`, and that the environment name is exactly `practice` in both Settings and the workflow.

## 6. Optional: see a typo create an empty environment

1. Make a new branch. In the workflow, change `environment: practice` to `environment: practise` (a typo). Commit and push the branch, but do not open a pull request.
2. Run that version of the file, and read its log:

```bash
gh workflow run secrets-practice.yml --ref <your-branch>
```

3. The job runs and prints `0 characters`. In **Settings > Environments** you will now see a new environment called `practise`, with no rules and no secrets. GitHub made it for you.
4. Clean up: delete the `practise` environment in Settings, and delete the branch.

## Check my work

Set `PRACTICE_REPO` in `.env`, then press **Check my work**. It runs read-only `gh` calls. It never reads a secret value, and GitHub's API never returns one:

- The environment `practice` exists in your repo.
- The environment `practice` has a secret named `PRACTICE_TOKEN` (the name only).
- The file `.github/workflows/secrets-practice.yml` on the default branch has a top-level `permissions:` block with exactly one entry, `contents: read` (one space after the colon), and a job with the line `environment: practice`. A job-level `permissions:` block does not count, and neither do `read-all` or `{}`.
- At least one run of `secrets-practice.yml` finished with the result `success`.
