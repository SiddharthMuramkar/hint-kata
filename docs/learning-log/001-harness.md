### PR — chore(harness): Claude Code harness
What changed: Added the files that tell Claude Code how to work on this repo: `CLAUDE.md` (the project brief Claude reads at
the start of every session), four subagent definitions (`builder`, `content-writer`, `diff-reviewer`, `second-opinion`),
four rule files in `.claude/rules/`, a hook that formats and lints every Python file Claude edits, eight hookify guard
rules (no sudo, no `rm -rf`, no force-push, no push to main, no reading or editing `.env`, no printing secrets, and no
stopping before tests were run), `.claude/settings.json` (model, permissions, plugins), an empty `.mcp.json`, `.env.example`
and `.worktreeinclude`.
Why: Builds run unattended in separate git worktrees. The harness keeps them on the right model, lets safe commands run
without prompts, blocks dangerous ones, and keeps secrets out of reach. Without it every task would stall on a prompt or
risk touching `main` or `.env`.
Left out on purpose: the FastAPI agent skill (`uvx library-skills`) is deferred to the first FastAPI lesson task, because FastAPI is not installed yet. It is noted in `docs/PARKING_LOT.md`. Also note that the "stop and run tests" rule only fires for the main session, not for subagents; CI is the real test gate.
Read first: `CLAUDE.md`, then `docs/HARNESS.md` for the reason behind each piece.
