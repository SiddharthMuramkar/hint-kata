# Task: a nightly workflow you can also run by hand

You will add a workflow to your practice repo that has a schedule, a manual trigger, a concurrency group and a read-only token. It prints the date. Then you start it by hand with `gh workflow run` and watch it finish.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. If you do not have it yet, stop here and do the setup in lesson GH1 first. The checker below needs it.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code.

No secrets are needed for this task. Do not add any.

## 1. Open the repo and make a branch

1. In VS Code, choose **File > Open Folder** and open your practice repo folder.
2. Open the terminal with **View > Terminal**.
3. Run:

```bash
git switch main
git pull
git switch -c add-nightly
```

## 2. Create the workflow file

1. In the Explorer, create the file `.github/workflows/nightly.yml`. VS Code makes the folders for you when you type the whole path in the new-file box.
2. Paste this into it:

```yaml
name: Nightly
on:
  schedule:
    - cron: "23 3 * * *" # 03:23 UTC every day. Off the hour on purpose.
  workflow_dispatch:
    inputs:
      note:
        description: "A short note to print in the log"
        required: false
        default: "run by hand"
        type: string
concurrency:
  group: nightly
  cancel-in-progress: false
permissions:
  contents: read
jobs:
  say-date:
    name: say date
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Print the date
        env:
          NOTE: ${{ inputs.note }}
        run: |
          date -u
          echo "note: ${NOTE:-none}"
```

Five things to notice:

- The `cron` line has five fields. The minute is `23`, not `0`, because the start of the hour is a busy time. You may pick another minute, but not `0`.
- `workflow_dispatch` is what lets you start it by hand. It has one input, `note`.
- The `concurrency` group is called `nightly`, so only one run of this workflow is active at a time. `cancel-in-progress: false` leaves a running job to finish.
- The top-level `permissions:` block has one line, `contents: read`. The job reads no files and writes nothing, so it needs no more.
- The input goes in through `env:` and is read as `$NOTE`. The script never puts `${{ inputs.note }}` inside the shell text.

## 3. Open a pull request and merge it

```bash
git add .github/workflows/nightly.yml
git commit -m "ci: add nightly workflow"
git push -u origin add-nightly
gh pr create --fill
```

If you did GH2, your `checks` workflow runs on this pull request. Wait for it with `gh pr checks --watch`. Then merge. Your GH1 ruleset allows squash merges:

```bash
gh pr merge --squash --delete-branch
git switch main
git pull
```

A scheduled or manual run only starts once the file is on the default branch. That is why you merge first.

## 4. Run it by hand and watch it

```bash
gh workflow run nightly.yml -f note="my first run"
sleep 5
gh run list --workflow nightly.yml --limit 1
```

Copy the run id from the list. The event column says `workflow_dispatch`. Then:

```bash
gh run watch <run-id>
gh run view <run-id> --log
```

In the log, find the date line and the line `note: my first run`. The run should end with the result `success`.

If `gh workflow run` cannot find the workflow, the file is not on the default branch yet. If it complains about a missing `workflow_dispatch` trigger, look at the `on:` block for a typo.

## 5. Optional: see the group make a run wait

1. On a new branch, add a step to the job, before the print step: `- run: sleep 60`. Commit, push and merge it like before.
2. Start two runs one after the other:

```bash
gh workflow run nightly.yml -f note="first"
gh workflow run nightly.yml -f note="second"
gh run list --workflow nightly.yml --limit 2
```

3. The first run goes first. The second waits in the `nightly` group until the first ends. The docs call a waiting run `pending`.
4. Remove the `sleep 60` step again when you are done.

## 6. Optional: look for the scheduled run

After the next 03:23 UTC (or the minute you chose), look at the run list. A run from the schedule shows the event `schedule`. It may start a little late. If your repo is public and idle, remember the 60-day rule from the lesson: `gh workflow list --all` shows a workflow that GitHub has switched off.

## Check my work

Set `PRACTICE_REPO` in `.env`, then press **Check my work**. It runs read-only `gh` calls:

- The file `.github/workflows/nightly.yml` on the default branch has a line `schedule:`, a line `workflow_dispatch:` and a line `concurrency:`. Lines that are only comments do not count.
- The file has a top-level `permissions:` block with exactly one entry, `contents: read`. A job-level block, `read-all`, and extra entries do not count.
- The run list of `nightly.yml` has at least one run with the event `workflow_dispatch` and the result `success`. A scheduled run alone is not enough, so run the workflow by hand.
