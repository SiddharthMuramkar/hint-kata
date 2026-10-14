# Hint Kata — Claude Code harness

What runs the build, why each piece exists, and what was rejected. Facts checked 2026-10-14 against
code.claude.com (Claude Code 2.1.299 installed). Details and sources: `docs/research/claude-code-features.md`.

## 0. Fresh-clone setup (do this once per machine)
1. Open the folder in VS Code. In the integrated terminal run `claude`. Accept the workspace-trust dialog
   (project settings, hooks, plugins and `claude -w` are ignored until you do).
2. Install the two external-source plugins (relative-path plugins load by themselves):
   ```bash
   claude plugin install pydantic-ai@claude-plugins-official --scope project
   ```
   ```bash
   claude plugin marketplace add Octen-Team/octen-mcp --scope project && claude plugin install octen@octen --scope project
   ```
   Then `/reload-plugins` and `claude plugin list`.
3. `uv sync --locked`. Copy `.env.example` to `.env` and fill the values yourself (never paste secrets into chat).
4. Check `/tasks` while agents run to confirm each one's real model. Make sure `CLAUDE_CODE_SUBAGENT_MODEL` is not exported in your shell.

## 1. Project settings — `.claude/settings.json` (committed)
| Key | Value | Why |
|---|---|---|
| `model` / `effortLevel` | `fable` / `high` | Fable carries judgment in the main session. |
| `fallbackModel` | `["sonnet"]` | Overload errors otherwise kill subagents. |
| `env` | `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=3`, `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS=3` | 24 GB Mac; each worktree has its own `.venv`. |
| `permissions.defaultMode` | **not set** | Auto mode is the built-in interactive default (v2.1.283+) and cannot come from project files; any other value would override it. |
| `outputStyle` | **not set** | "Learning" pauses at `TODO(human)` and stalls unattended runs. Use `/output-style Learning` by hand in study sessions. |
| `enabledPlugins` / `extraKnownMarketplaces` | see §5 | So a fresh clone knows what to load. |
| `permissions.allow` / `deny` | see §4 | Unattended runs must not stall on safe commands, and must not be able to loosen guardrails. |
| `hooks` | see §3 | Format + lint after every edit. |

## 2. Subagents — `.claude/agents/` (first needed: M1)
| Agent | Model / effort | Tools | Job |
|---|---|---|---|
| `builder` | `claude-sonnet-5-5` / high, `isolation: worktree` | Read, Edit, Write, Bash, Grep, Glob | Implements one issue: code + tests, runs checks, commits, pushes, opens the PR with a plain-English body. |
| `content-writer` | `claude-sonnet-5-5` / high, `isolation: worktree` | Read, Edit, Write, Bash, Grep, Glob, WebFetch, Octen/Firecrawl tools | Writes one lesson set from the cached sources in our own words with attribution; runs the content validators. |
| `diff-reviewer` | `claude-fable-5-1` / high | Read, Grep, Glob, Bash (read-only use) | Reviews a PR diff for correctness, tests, scope creep, secrets, licence/attribution; returns a findings list. |
| `second-opinion` | `claude-opus-5-5` / high | Read, Grep, Glob | Independent review of risky changes only (settings/permissions, CI permissions, schema, secrets handling). Invoked by name; description says "only when explicitly asked". |
Why not more: every extra agent costs usage; these four cover build, content, judgment and risk.
Model routing is set in frontmatter with full IDs (the env var is only a default since v2.1.251). Verify with `/tasks`.
Known caveat: Fable may bill to usage credits on some plans and its consent prompt expires in background sessions; if that happens the main session asks you once.

## 3. Hooks — `.claude/settings.json` + `.claude/hooks/` (M1)
- **PostToolUse `Edit|Write` → `ruff_after_edit.py`** (exec form, `onFailure: "block"`, timeout 60 s). Runs
  `uv run --frozen ruff format` then `ruff check --fix` on edited `.py` files; remaining errors go back to Claude via
  exit 2. Python with `from __future__ import annotations` so it also runs on macOS's `/usr/bin/python3` 3.9.
- Why no PreToolUse hooks of our own: hookify (below) covers the pattern blocks; `permissions.deny` covers reads.
- Tested once by piping sample JSON (`echo '{"tool_name":"Edit","tool_input":{"file_path":"x.py"}}' | python3 .claude/hooks/ruff_after_edit.py; echo $?`); results pasted in the M1 PR.

## 4. Hookify rules — `.claude/hookify.<name>.local.md` (M1, committed on purpose)
Hookify can only warn or block; it reads rules from `.claude/` relative to the working directory, so the files are
committed (and `.gitignore` must not exclude `*.local.md`) so every worktree and clone has them.
| Rule | Event / action | Pattern (regex) |
|---|---|---|
| `block-sudo` | bash / block | `(^\|[;&\|]\s*)sudo\s` |
| `block-rm-rf` | bash / block | `rm\s+-[a-zA-Z]*r[a-zA-Z]*f\|rm\s+-[a-zA-Z]*f[a-zA-Z]*r` |
| `block-force-push` | bash / block | `git\s+push\b.*(\s-f\b\|--force)` |
| `block-push-main` | bash / block | `git\s+push\b.*\b(main\|master)\b` |
| `block-env-bash` | bash / block | `(cat\|head\|tail\|less\|more\|sed\|grep\|source\|\.)\s+[^\|;]*\.env(\.[a-z]+)?\b` (excluding `.env.example`) |
| `block-env-edit` | file / block | `file_path` regex `\.env($\|\.(?!example))` |
| `block-print-secrets` | bash / block | `\b(printenv\|env)\s*$\|echo\s+\$\{?\w*(KEY\|TOKEN\|SECRET)` |
| `stop-run-tests` | stop / block | transcript `not_contains` `pytest` |
Gaps hookify cannot close (documented so nobody assumes otherwise): the Read tool (covered by `permissions.deny`),
`/usr/bin/git`, `sh -c '…'`, scripts that open files. GitHub rulesets are the real lock on `main`.

## 5. Plugins (M1)
| Plugin | Source | Why | How it loads |
|---|---|---|---|
| `hookify@claude-plugins-official` | official (relative path) | guard rails above | auto after trust |
| `frontend-design@claude-plugins-official` | official (relative) | UI tasks (dark theme, lesson layout) | auto after trust |
| `ponytail@ponytail` | `DietrichGebert/ponytail` | least code that does the job; `/ponytail ultra` is in CLAUDE.md | marketplace declared; already installed at user scope |
| `pydantic-ai@claude-plugins-official` | external (git-subdir) | V2-accurate Pydantic AI code | `claude plugin install … --scope project` |
| `octen@octen` | `Octen-Team/octen-mcp` (relative) | doc page fetching and research during content tasks | marketplace declared; OAuth on first call |
| FastAPI agent skill | `uvx library-skills` into `.claude/skills` | FastAPI conventions matching the installed version | committed file |
Firecrawl and Tavily: used through the claude.ai connectors already attached to the owner's account (no keys to
store). The official plugins exist (`firecrawl@…`, `tavily@…`) and need API keys; optional.
Phase 2: `neon@claude-plugins-official`, `vercel@claude-plugins-official`, `logfire@claude-plugins-official`.

## 6. MCP servers — `.mcp.json` (M1)
`{"mcpServers": {}}`. Reasons: `gh` CLI (logged in) covers everything GitHub needs and the GitHub MCP server would
need a separate PAT; Firecrawl/Tavily/Octen arrive via connectors or plugins; Neon and Vercel are phase 2.
Secrets never go in `.mcp.json`; when a server is added it uses `${VAR}` references with project-specific names
(not `GITHUB_TOKEN`/`ANTHROPIC_*`, which Claude Code reads as empty in remote headers).

## 7. Permissions (M1)
Allow (no prompts in unattended runs): `Bash(uv sync *)`, `Bash(uv lock *)`, `Bash(uv run pytest *)`,
`Bash(uv run ruff *)`, `Bash(uv run ty *)`, `Bash(uv run fastapi *)`, `Bash(uv run python scripts/*)`,
`Bash(git status *)`, `Bash(git diff *)`, `Bash(git log *)`, `Bash(git add *)`, `Bash(git commit *)`,
`Bash(git switch *)`, `Bash(git fetch *)`, `Bash(git worktree *)`, `Bash(git push -u origin *)`,
`Bash(gh pr create *)`, `Bash(gh pr view *)`, `Bash(gh pr checks *)`, `Bash(gh pr list *)`, `Bash(gh pr merge --auto *)`,
`Bash(gh issue *)`, `Bash(gh run list *)`, `Bash(gh run view *)`, `Bash(gh api repos/* --jq *)`.
Deny (agents run with the owner's admin token, so these stop them loosening the guardrails): `Bash(sudo *)`,
`Bash(git push --force *)`, `Bash(git push -f *)`, `Bash(git reset --hard *)`, `Bash(gh repo delete *)`,
`Bash(gh repo edit *)`, `Bash(gh api -X DELETE *)`, `Bash(gh api -X PATCH *)`, `Bash(gh api -X PUT *)`,
`Bash(gh pr merge --admin *)`, `Bash(gh secret *)`, `Read(./.env)`, `Read(./.env.*)`, `!Read(./.env.example)`,
`Edit(.claude/settings.json)`, `Edit(.claude/hooks/**)`, `Edit(.claude/hookify.*)`, `Edit(.github/workflows/**)` is NOT denied (CI changes go through PR review instead).
Never add `Bash(uv run *)` or `Bash(python *)`: runner prefixes pass anything through.
Ask rules are avoided: in auto mode they prompt and stall.

## 8. GitHub Actions (M0/M1)
| Workflow | Trigger | Job | Why |
|---|---|---|---|
| `ci.yml` | `pull_request`, `push` to main | `checks`: `uv sync --locked`, `ruff check`, `ruff format --check`, `ty check`, `pytest -q` | the required status check; SHA-pinned actions; `permissions: contents: read`; concurrency cancel on PRs |
| CodeQL default setup | managed by GitHub | python + actions | free on public repos; no workflow file; gate with a ruleset `code_scanning` rule after the first analysis |
| `dependabot.yml` | weekly | uv + github-actions, grouped | keep pins fresh; Dependabot PRs are reviewed, not auto-merged |
| `evals.yml` | `workflow_dispatch` only | runs `evals/` with `OPENROUTER_API_KEY` secret | costs money; never on every PR |
Runners vs the Mac: CI runs on GitHub (free for public repos). The Claude Code GitHub Action was **rejected**: with an
OAuth token it bills the same weekly subscription limits as local Claude Code, and it adds a public prompt-injection surface.

## 9. /goal and /loop (M1 onward)
- `/goal` judges only from the transcript, has no turn cap unless you write one, and clears on auth/credit/model errors.
  Use the line in `docs/PLAN.md`. Keep the session open.
- `/loop` fires only while the session is open and idle, expires after 7 days, is not restored on resume. Use it for
  CI watching during a build session; for anything that must outlive a session use GitHub Actions.
- Auto-mode caveat: the default classifier blocks "merging a PR no human has approved". Bootstrap step 0.6 checks whether
  it is soft (then explicit intent in the go prompt + a user-scope `autoMode.allow` entry fixes it) or hard (then you run
  the `gh pr merge --auto` lines I print).

## 10. Worktrees and RAM
- `claude -w <name>` (or subagent `isolation: worktree`) → `.claude/worktrees/<name>` (gitignored), branched from origin main.
  `.worktreeinclude` lists `.env` so each worktree gets it (gitignored files only).
- Cap: 2 worker worktrees at once. Each runs `uv sync` (own `.venv`). Don't run two dev servers unless needed.
- Clean up with `git worktree list` / `git worktree remove`.

## 11. Rejected (and why)
| Item | Why not |
|---|---|
| Learning output style in settings | stops at `TODO(human)`; stalls unattended runs |
| Agent teams | experimental, token-hungry, changes how named subagents behave |
| Sandbox | friction (network allowlists, SSH) on a non-admin Mac; revisit if secrets exposure grows |
| claude-code-action | same usage limits as local Claude Code; public injection surface |
| GitHub MCP server | duplicates `gh`; needs a PAT |
| `Bash(uv run *)` allow rule | allows any command |
| Ask rules | stall auto mode; deny instead |
| React/Vite/Next.js, htmx | no strong reason; JS build or GET-only SSE |
| Pyodide / Monaco | untested with Pydantic AI; heavy |
| Vector DB in phase 1 | tutor uses the lesson text; RAG is phase 2 |
| Logfire as storage | 30-day retention, query limits |
| `CLAUDE_CODE_SUBAGENT_MODEL` | would override per-agent routing if forced; keep unset |
