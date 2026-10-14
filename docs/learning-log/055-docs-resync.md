Hint Kata now re-checks its source docs every week. A new workflow, `.github/workflows/docs-resync.yml`, runs on Monday at 06:17 UTC (or when you run `gh workflow run docs-resync.yml`). Its `plan` job downloads every page in `content/sources.yaml` and records the new hashes. Only if a page really changed does it open one pull request on the branch `docs-resync`. The PR body is a report from the new `scripts/resync_report.py`: which pages changed, which lessons cite them (so their quizzes may be stale), and which pages failed to download. When you merge that PR, the `embed` job re-embeds just the changed pages. It does that only if the repository secrets `OPENROUTER_API_KEY` and `DATABASE_URL_UNPOOLED` exist and `scripts/ingest.py` is on `main` (issue #53 builds it). Otherwise it skips quietly. The plan job has no secrets, write access on that job only, a concurrency group and a timeout.

Two things you need to know. First, a PR opened by a workflow with the built-in `GITHUB_TOKEN` does not start the `checks` workflow on its own. GitHub holds it until you click **Approve workflows to run**, push an empty commit, or close and reopen the PR. The PR body says so. A personal token that avoids this is described in the runbook, but it is not required. Second, the repo setting "Allow GitHub Actions to create and approve pull requests" is off today. Tick it once under Settings > Actions > General, or the PR step fails. GitHub may also hold the very first run of a new workflow until you approve it.

I made one small change outside the new files. `scripts/fetch_docs.py` used to stop at the first page that failed. Now it prints `FAILED <id>`, skips that page, finishes the rest and exits 1. That is how the report learns which pages failed. A new test covers it.

Read `docs/runbooks/docs-resync.md` first. It has the setup checklist, how to run the workflow by hand, the 60-day auto-disable rule for scheduled workflows on public repos and how to turn it back on.

One lesson learned: `fetched_at` changes on every run, so "did `content/sources.yaml` change?" is always yes, and a weekly PR would open even when no doc moved. The job asks the question that matters instead: "did any `sha256` change?". When a trigger is noisy, test the thing you care about, not the file that holds it.

Closes #55

🤖 Generated with [Claude Code](https://claude.com/claude-code)
