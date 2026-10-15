# Git and PRs

- One issue, one branch `issue-<n>-<slug>`, one PR. Never push to main. Never force-push. Merges are squash only.
- Commit message starts with a type (`feat:`, `fix:`, `chore(scope):`, `test:`, `docs:`) and ends with the trailer:
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`
- PR body is a plain-English lesson: what changed, why, which file to read first. It ends with `Closes #<n>` and then the line:
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
- Every PR adds exactly one new file `docs/learning-log/<issue-number-3-digits>-<slug>.md` holding the PR body text. Nobody edits `docs/LEARNING_LOG.md` or `docs/PROGRESS.md` inside a task PR; the main session updates them between tasks. This avoids merge conflicts.
- Out-of-scope ideas go in `docs/PARKING_LOT.md`, not in the PR.
