## What changed

Two hookify guard rails were blocking harmless commands, so I tightened their regexes. Nothing else in the harness changed.

- `block-env-bash`: the `.` alternative (shell shorthand for `source`) matched any ". " followed later by ".env" anywhere in the command, for example the end of a sentence inside a `gh issue create --body "..."` text. The pattern now begins with `(^|[;&|]\s*)`, so `cat`, `grep`, `source` and `.` only count when they start a shell segment.
- `block-push-main`: `git\s+push\b.*main` matched a compound command such as `git push -u origin x && gh pr create --base main`. The `.*` is now `[^;&|]*`, so `main` must be in the same segment as `git push`.
- `block-print-secrets`: verified, no change needed.

## Why this matters

Hookify patterns are Python regexes, searched (not matched from the start) across the WHOLE Bash command text, so any rule that uses `.*` can reach across `&&`, `;`, `|` and even into quoted text. The fix is to stop a match at a segment boundary. Side effect to remember: run `git push` as its own command (noted in the gaps line of HARNESS.md section 4).

## Read first

`docs/HARNESS.md` section 4 (the two updated table rows and the gaps line), then the two rule files in `.claude/` (`hookify.block-env-bash.local.md`, `hookify.block-push-main.local.md`).

## Test results

Each command was piped as PreToolUse JSON into the real hook (`python3 <hookify plugin>/hooks/pretooluse.py`) from the worktree root.

| Rule | Command | Expected | Actual | Result |
|---|---|---|---|---|
| block-env-bash | `cat .env` | block | block | PASS |
| block-env-bash | `ls && cat .env` | block | block | PASS |
| block-env-bash | `grep KEY .env.local` | block | block | PASS |
| block-env-bash | `source .env` | block | block | PASS |
| block-env-bash | `. .env` | block | block | PASS |
| block-env-bash | `cat .env.example` | allow | allow | PASS |
| block-env-bash | `gh issue create --body "see docs/PLAN.md. copy the key into .env then run"` | allow | allow | PASS |
| block-push-main | `git push origin main` | block | block | PASS |
| block-push-main | `git push origin HEAD:main` | block | block | PASS |
| block-push-main | `git push --set-upstream origin main` | block | block | PASS |
| block-push-main | `git push origin master` | block | block | PASS |
| block-push-main | `git push -u origin issue-3-main-py` | allow | allow | PASS |
| block-push-main | `git push -u origin x && gh pr create --base main` | allow | allow | PASS |
| block-print-secrets | `echo "hello world"` | allow | allow | PASS |
| block-print-secrets | `env FOO=1 pytest` | allow | allow | PASS |
| block-print-secrets | `printenv` | block | block | PASS |
| block-print-secrets | `env \| grep X` | block | block | PASS |
| block-print-secrets | `echo $OPENROUTER_API_KEY` | block | block | PASS |

🤖 Generated with [Claude Code](https://claude.com/claude-code)
