# Runbook: weekly docs re-sync

The workflow is `.github/workflows/docs-resync.yml`. The scripts are `scripts/fetch_docs.py` and `scripts/resync_report.py`. Nothing here holds secrets.

## What it does
Two jobs in one file, two kinds of trigger.

**`plan`** runs every Monday at 06:17 UTC (`cron: "17 6 * * 1"`) and on demand.
1. Downloads every page listed in `content/sources.yaml` with `fetch_docs.py --update`. That refreshes `sha256` and `fetched_at`.
2. Runs `resync_report.py`. It compares the new manifest with the one on `main` and writes a Markdown report: which source ids changed, which lessons cite them (their quizzes may be stale), which ids failed to download.
3. If any `sha256` changed, it opens or updates one pull request from the branch `docs-resync`, with the report as the PR body. If nothing changed, it opens nothing. (`fetched_at` changes on every run, so the file always differs. Only a new `sha256` counts as news.)
4. If a page failed to download, the run ends red, so you get GitHub's failure email.

**`embed`** runs on every push to `main` that touches `content/sources.yaml`. That is the merge of a plan PR, or any content PR that adds a source.
1. A small `gate` job checks that the repository secrets `OPENROUTER_API_KEY` and `DATABASE_URL_UNPOOLED` exist. If one is missing, `embed` is skipped and the run stays green.
2. `embed` finds the ids whose `sha256` changed in that push, downloads just those pages, then runs `scripts/ingest.py --only <ids>`. Only the ingest step sees the secrets.
3. If `scripts/ingest.py` is not on `main` yet, the step prints a notice and does nothing.

The plan job never sees repository secrets. Its write permission (`contents` and `pull-requests`) is set on that job only; every other job is read-only.

## One-time setup for the owner
- [ ] In the repo go to Settings > Actions > General > Workflow permissions. Tick **Allow GitHub Actions to create and approve pull requests**. It is off today. Without it the PR step fails with "GitHub Actions is not permitted to create or approve pull requests".
- [ ] To turn on embedding, add two repository secrets (Settings > Secrets and variables > Actions): `OPENROUTER_API_KEY` and `DATABASE_URL_UNPOOLED` (the Neon direct URL). Type the values yourself. Skip this until `scripts/ingest.py` is on `main`.
- [ ] After the workflow is on `main`, run it once by hand (next section) and read the report.

GitHub may hold the first run of a new workflow file, or a run it flags as suspicious, until a repo collaborator approves it in the browser. If a run sits in "waiting", open it on the Actions tab and click **Approve and run**.

## Run it by hand
The workflow must be on `main`. It only runs from `main`; a run from another branch is skipped.

```
gh workflow run docs-resync.yml
gh run list --workflow docs-resync.yml --limit 3
gh run watch
```

Use `gh workflow list --all` to see whether it is active or disabled.

## Reviewing a plan PR
1. Read the report in the PR body. Open each changed source and each lesson on the list.
2. If a lesson needs new text or quiz items, fix it in a normal issue and PR. The plan PR only changes `content/sources.yaml`.
3. Make CI run (next section), wait for `checks` to pass, then squash-merge. The merge triggers `embed`.

## PRs opened with GITHUB_TOKEN do not run `checks`
The plan job opens the PR with the default `GITHUB_TOKEN`. GitHub does not let that token start other workflows, so the `checks` workflow does not run on its own. Since June 2026 GitHub still creates the runs, but holds them as "approval required". Pick one:
- Click **Approve workflows to run** in the PR merge box.
- Push an empty commit to the branch from your own login:
  ```
  git fetch origin docs-resync
  git switch docs-resync
  git commit --allow-empty -m "ci: run checks"
  git push origin docs-resync
  ```
  A later weekly run rebuilds the branch from `main` and may drop this commit. That is fine.
- Close the PR and reopen it.

The PR body says this too, so you see it at the moment you need it.

### Optional: a token that starts CI by itself
You do not need this. If the click gets tiresome:
1. Create a fine-grained personal access token for this repository only, with Contents: read and write and Pull requests: read and write. Set a short expiry.
2. Save it as the repository secret `DOCS_RESYNC_TOKEN`.
3. In `docs-resync.yml`, change `token: ${{ github.token }}` in the PR step to `token: ${{ secrets.DOCS_RESYNC_TOKEN }}`.

The cost: the plan job now holds a secret. It only runs code from `main`, so that is acceptable, but it is why the default is `GITHUB_TOKEN`. A GitHub App token is the stricter option.

## The 60-day rule
On a public repo, GitHub switches off scheduled workflows after 60 days with no repository activity. It emails a warning first. Weekly merged plan PRs count as activity, but a quiet repo can still hit it.

To check and turn it back on:
```
gh workflow list --all
gh workflow enable docs-resync.yml
```
The same button is on the Actions tab: pick "Docs re-sync", then **Enable workflow**. Scheduled runs can also be late or dropped when GitHub is busy. That is normal. The next Monday catches up, because the plan compares hashes, not dates.

## When something goes wrong
- **Run is red and the PR lists "Failed to fetch".** A page did not download (network, a moved URL). Its manifest entry is untouched. Re-run: `gh run rerun <run-id>`. If it keeps failing, fix `fetch_url` in `content/sources.yaml`.
- **PR step fails with "not permitted to create or approve pull requests".** Do the first setup item.
- **Two embed runs overlap or one is dropped.** Runs queue, one at a time, never cancelled. GitHub keeps only one waiting run, so two merges inside one embed run can skip the middle one. Run the ingest CLI by hand for that id.
- **A source was removed from the manifest.** `embed` only names changed ids, so it does not remove that source's chunks. Remove them by hand with the ingest CLI.

## Pinned actions
Every action is pinned to a full commit SHA, with its tag in a comment. Dependabot's `github-actions` entry proposes bumps.
- `actions/checkout` v7.0.1
- `astral-sh/setup-uv` v10.3.0 (uv 0.13.1)
- `peter-evans/create-pull-request` v8.1.1 (`5f6978faf089d4d20b00c7766989d076bb2fc7f1`)
