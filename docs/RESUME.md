# Resume here

Phase 1 + 2 code is complete (36 lessons on `main`, no open PRs). For maintenance, open a Muse Code
session in the repo folder and paste section B. Section A is kept as build history only.

## B. Continue in Muse (current)

```text
Read CLAUDE.md and docs/PROGRESS.md. Run `git status`, `gh pr list --state open -R SiddharthMuramkar/hint-kata` and `gh issue list --state open -R SiddharthMuramkar/hint-kata`. Phase 1 + 2 code is done; open issues are owner-only (#19 calibration needs OPENROUTER_API_KEY, #58 domain needs an explicit yes) and Phase 3 outlines (#59–#61, do not build without a new decision). For any change: one issue, one branch, one PR; the four checks (`uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run pytest -q`) must pass; never commit, push or merge without my explicit yes; never read or print secrets — give me the exact command to type them myself. Report each finished task in one short beginner-friendly paragraph.
```

## A. First start (history — the repo has no commits yet)

```text
Read docs/PLAN.md, docs/HARNESS.md and docs/SPEC.md. Start Phase 1 at M0 Bootstrap and continue through M1 and onward without stopping. Rules: every task is a GitHub issue, built in its own worktree and branch, and merged by its own PR; tests, ruff and ty must pass locally before each PR; the diff-reviewer agent (Fable) reviews every PR and the builder fixes what it finds; I authorise you to run `gh pr merge --auto --squash` on a PR once that review passes and CI is green; push after every finished task; keep docs/PROGRESS.md and docs/LEARNING_LOG.md current in each PR; put out-of-spec ideas in docs/PARKING_LOT.md; at most 2 parallel workers. Ask me only for secrets (give me the exact command), purchases, or deletions. If a step needs admin rights, stop and tell me.
```

## Old B (history). Continue after a cut-off in Claude Code — superseded by section B above

```text
Read CLAUDE.md, docs/PROGRESS.md and docs/PLAN.md. Run `git status`, `git worktree list`, `gh pr list --state open` and `gh issue list --milestone "Phase 2" --state open` (Phase 1 is done except #19, which needs the owner's API key). Finish anything under "In flight" in PROGRESS.md (check its worktree and PR first), then take the next open issue in PLAN order. Same rules as docs/RESUME.md section A. Report what you did at the end of each task in one short paragraph.
```

Before anything else, run `uv run python scripts/docs_status.py --progress`: it prints lessons per track, open PRs and open issues by milestone straight from GitHub.

## C. Owner-only steps (secrets and accounts)
- Grader calibration: follow the steps on issue #19 (`gh issue view 19`).
- Neon and Vercel: docs/runbooks/neon.md and docs/runbooks/vercel.md list what only you can do (typing the database URLs and API keys into the local env file and GitHub secrets, linking the Vercel project). Nothing is bought or linked without you.

## D. If something looks broken
- Red CI on main: `/loop 15m run gh run list --branch main --limit 3; if the newest run failed read gh run view <id> --log-failed, fix it on a new branch in a worktree, open a PR, report the URL; else say CI is green`
- A held workflow run (GitHub "approval required"): approve it in the browser under Actions; nothing to fix.
- Usage limit hit mid-task: nothing to do; the worktree and branch are on disk and usually pushed. Use prompt B.

## E. Run the site on your Mac
- Once per clone: `uv sync --locked --all-groups`.
- Start it: `uv run fastapi dev`. Open http://127.0.0.1:8000 (the health check is http://127.0.0.1:8000/healthz and answers `{"ok":true}`). It reloads when you save a file. Press Ctrl+C in the terminal to stop it.
- Production-style run, no reload: `uv run fastapi run --port 8765`. It listens on all network interfaces, so use `dev` for everyday work.
- If `fastapi dev` says "please install fastapi[standard]", the `fastapi-cli` pin is missing from your environment. Run `uv sync --locked --all-groups` again. Do not add `fastapi[standard]`; it pulls in extra packages this app does not use.
- Fallback that does not need `fastapi-cli`: `uv run uvicorn app.main:app --reload`, then open http://127.0.0.1:8000.
