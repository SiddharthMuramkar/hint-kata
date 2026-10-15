## What changed

The repo moved from the GitHub account `siddharth-0044` to `SiddharthMuramkar`, and the owner asked that Opus 5.5 make the judgement calls while Sonnet 5.5 keeps writing all code and content.

- The old repo name `siddharth-0044/hint-kata` is now `SiddharthMuramkar/hint-kata` in the live places: `scripts/docs_status.py`, `scripts/fetch_docs.py`, two runbooks, and the `gh -R` and `gh api repos/...` commands in lessons GH7 and GH8.
- Routing now says Opus 5.5 judges: `.claude/agents/diff-reviewer.md` uses `claude-opus-5-5`, "Model routing" in `CLAUDE.md` and "How the build runs" in `docs/PLAN.md` are updated, and the commit trailer in `.claude/rules/git.md` is `Co-Authored-By: Claude Opus 5.5`.

## Why

Commands that point at the old name only work through GitHub's redirect, and the docs should name who really decides.

## Left alone on purpose

History stays as it was, because old URLs redirect: `content/github/gh1-ready-to-merge/trace.json`, older learning-log files and dated observations in lessons.

Read first: `CLAUDE.md`, section "Model routing".

Closes #133

🤖 Generated with [Claude Code](https://claude.com/claude-code)
