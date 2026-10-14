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
Read first: `CLAUDE.md`, then `docs/HARNESS.md` for the reason behind each piece.
