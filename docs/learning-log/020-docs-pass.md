# 020 — Docs pass: phase 1 closed, phase 2 opened

## What changed
- `docs/PROGRESS.md` now says phase 1 is done (with the PR number for each piece) and lists what phase 2 has in flight.
- `docs/LEARNING_LOG.md` is a generated index: one row per merged PR, in merge order, linking to its file under `docs/learning-log/`.
- `docs/RESUME.md` prompt B now points at the "Phase 2" milestone, and a new section C lists the steps only the owner can do (API key, Neon, Vercel).

## Why
A fresh session (or a fresh person) reads three files to find out where the project is: PROGRESS for status, LEARNING_LOG for the story so far, RESUME for the first command to run. If those drift, the "resume after a cut-off" promise breaks.

## Read first
`docs/PROGRESS.md`, then the index in `docs/LEARNING_LOG.md`.

## Lesson
Keep status docs out of task PRs. Every task PR adds its own file under `docs/learning-log/`, and the main session regenerates the index between tasks. Six parallel PRs editing the same index file would conflict on every merge.
