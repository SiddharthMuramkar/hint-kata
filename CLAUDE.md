# Hint Kata

Hint Kata is a small website that teaches Pydantic AI, FastAPI and GitHub flow through short lessons: read, quiz,
think deeper, ask a tutor that only gives hints, run hands-on checks, and review what you missed on a schedule. It is built
in public by Claude Code and its owner is learning from the build. Spec: `docs/SPEC.md`. Plan: `docs/PLAN.md`.
Harness (why each config exists): `docs/HARNESS.md`.

## Stack (pinned; see `docs/SPEC.md` section 13)
- Python 3.13 managed by uv. FastAPI 0.143.x, Jinja2, built-in SSE, ~35 lines of vanilla JS.
- Pydantic AI 2.56 (V2) through OpenRouter. Agents in `app/agents/`: `tutor`, `grader`, `author`.
- SQLite (`data/hintkata.db`) behind a `Store` Protocol. `markdown-it-py` + Pygments for rendering.
- Dev tools: ruff 0.17.0, ty 0.0.87, pytest 9.1.1.

## Commands
```bash
uv sync --locked              # install (add --all-groups for dev tools)
uv run fastapi dev            # run the site
uv run pytest -q              # tests
uv run ruff check .           # lint
uv run ruff format --check .  # format check
uv run ty check               # type check
```
All four checks must pass before every commit.

## Repo layout
`app/` (main.py, routes/, agents/, store.py, markdown.py, templates/, static/) · `content/` (lessons, sources.yaml) ·
`traces/` · `scripts/` · `evals/` · `tests/` (unit, acceptance) · `docs/` · `.claude/` (agents, rules, hooks, settings).

## Conventions
Topic rules live in `.claude/rules/` and load by themselves:
- `python.md` — ruff, type hints, pytest, no model calls in tests.
- `agents.md` — Pydantic AI V2 rules (loads for `app/agents/`, `evals/`, `traces/`).
- `content.md` — own words, attribution, licences (loads for `content/`).
- `git.md` — branches, commits, PR body, learning-log file.

## Model routing
Fable judges (main session, reviews every diff, merges). Sonnet 5.5 at effort high builds (`builder`,
`content-writer`). Opus 5.5 is a rare second opinion on risky changes only (`second-opinion`). Check the real
model of each running agent with `/tasks`. Do not set `CLAUDE_CODE_SUBAGENT_MODEL`.

## Style
`/ponytail ultra` is the house style: the least code that does the job. No extra layers, options or files.

## PRs and the learning log
One issue, one branch, one PR, one worktree. The PR body is a short plain-English lesson (what changed, why, which file
to read first) ending with `Closes #<n>`. Every PR adds one new file `docs/learning-log/<nnn>-<slug>.md` with that text.
Do not edit `docs/LEARNING_LOG.md` or `docs/PROGRESS.md` in a task PR; the main session updates them between tasks.
Details: `.claude/rules/git.md`.

## Claude builds, the owner learns
Claude does all the building. There are no `[ME]` tasks for the owner. The owner reads PRs and the learning log and
learns from them, so write the PR body for a beginner. Out-of-scope ideas go in `docs/PARKING_LOT.md`.

## Secrets
Secrets live only in `.env` (local, gitignored) and GitHub secrets. The owner types the values; Claude never reads,
prints, edits or commits them. Add new variable names to `.env.example` (names only). `.env` reads and edits are denied
by `.claude/settings.json` and by hookify rules.

## Resume here
After a cut-off or in a fresh session, read `docs/RESUME.md` (the prompt to paste) and `docs/PROGRESS.md` (done, in
flight, next). Then run `git status`, `git worktree list`, `gh pr list --state open`.
