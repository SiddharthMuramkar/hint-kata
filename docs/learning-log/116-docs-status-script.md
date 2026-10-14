## What changed

A new script, `scripts/docs_status.py`, keeps the status docs honest. It has three modes.

- `--learning-log` rewrites the index `docs/LEARNING_LOG.md` from the merged pull requests on GitHub.
- `--progress` prints a status block (lessons per track, open PRs, open issues by milestone). It never writes a file. You paste what is new into `docs/PROGRESS.md`.
- `--check` exits 1 if the index would change. It is not part of CI yet.

How the index is built:

- Each merged PR owns the file `docs/learning-log/NNN-*.md`. NNN is the number in its `Closes #N` line, or else its own PR number, padded to three digits.
- Rows are in merge order, so a few early rows moved (for example #22 merged after #25).
- A row that already exists keeps its text word for word. The old row with a "—" instead of a PR number (the docs pass) is now filed under #76.
- Files that no merged PR claims are listed at the end under "Unmatched entries", so nothing is lost. This PR's own entry sits there until it merges.
- Running it twice changes nothing.

Also in this PR:

- `docs/LEARNING_LOG.md` is regenerated: 40 rows and 1 unmatched entry.
- `docs/PROGRESS.md` shows the real state: phase 1 done, phase 2 merged and in flight, the open issues that come next, and an owner-only steps section.
- `docs/RESUME.md` has one new line telling a fresh session to run the `--progress` command first.
- `tests/test_docs_status.py` covers the script with a recorded list of merged PRs. No test calls `gh`.

## Why

Every merged PR adds a file, so the index and the progress page fall behind unless someone edits them by hand. Now the index comes from GitHub, and the status numbers do too. Task PRs still must not touch these two pages. This is the one PR that does, to set them up.

## Read first

`scripts/docs_status.py`, the function `build_index`. It is about 25 lines and shows how a PR finds its entry file.

## Lesson

A generated page should be safe to regenerate. Keep what a person edited, give the same output on a second run, and add a `--check` that fails when the page is stale. Then nobody has to remember to update it. When two number systems disagree (issue numbers and PR numbers), write the rule down in one place and keep a tiny table for the exceptions, instead of fixing rows by hand.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
