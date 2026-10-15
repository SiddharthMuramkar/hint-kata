## What changed

Docs pass after finishing Phase 1 + 2 code from Muse: `docs/PROGRESS.md` now says 36 lessons
(12 per track) merged and deploy-ready, with the final batch (#125, #129, #131, #132, #135–#138,
#139, #140) recorded and the secret commands fixed to the current repo
`SiddharthMuramkar/hint-kata`. `docs/LEARNING_LOG.md` was regenerated with
`scripts/docs_status.py --learning-log` (67 rows, 0 unmatched). `CLAUDE.md` and `docs/RESUME.md`
now describe maintenance in Muse — one session, four checks, merges only with the owner's
explicit yes — instead of the historical Claude Code judge/builder split, which stays documented
in `docs/HARNESS.md`.

Verified on merged main before this pass: `ruff check`, `ruff format --check`, `ty check` and
`pytest -q` (981 passed, 30 Postgres-gated skipped locally) all pass; CI `checks` is green; the
site serves `/`, all 36 lesson pages and `/healthz` on SQLite with no secrets.

Why: the docs still described 18 lessons, open PRs, the old GitHub account in the owner secret
commands, and a paid-model workflow the owner no longer uses.

Read first: `docs/PROGRESS.md`.

Closes #20
