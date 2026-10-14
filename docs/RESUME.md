# Resume here

Paste one of these into a fresh Claude Code session opened in the repo folder (VS Code → integrated terminal → `claude`).

## A. First start (the repo has no commits yet)

```text
Read docs/PLAN.md, docs/HARNESS.md and docs/SPEC.md. Start Phase 1 at M0 Bootstrap and continue through M1 and onward without stopping. Rules: every task is a GitHub issue, built in its own worktree and branch, and merged by its own PR; tests, ruff and ty must pass locally before each PR; the diff-reviewer agent (Fable) reviews every PR and the builder fixes what it finds; I authorise you to run `gh pr merge --auto --squash` on a PR once that review passes and CI is green; push after every finished task; keep docs/PROGRESS.md and docs/LEARNING_LOG.md current in each PR; put out-of-spec ideas in docs/PARKING_LOT.md; at most 2 parallel workers. Ask me only for secrets (give me the exact command), purchases, or deletions. If a step needs admin rights, stop and tell me.
```

## B. Continue after a cut-off (the repo exists)

```text
Read CLAUDE.md, docs/PROGRESS.md and docs/PLAN.md. Run `git status`, `git worktree list`, `gh pr list --state open` and `gh issue list --milestone "Phase 1" --state open`. Finish anything under "In flight" in PROGRESS.md (check its worktree and PR first), then take the next open issue in PLAN order. Same rules as docs/RESUME.md section A. Report what you did at the end of each task in one short paragraph.
```

## C. If something looks broken
- Red CI on main: `/loop 15m run gh run list --branch main --limit 3; if the newest run failed read gh run view <id> --log-failed, fix it on a new branch in a worktree, open a PR, report the URL; else say CI is green`
- A held workflow run (GitHub "approval required"): approve it in the browser under Actions; nothing to fix.
- Usage limit hit mid-task: nothing to do; the worktree and branch are on disk and usually pushed. Use prompt B.
