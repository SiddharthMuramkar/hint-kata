This adds lesson GH11, "Claude in GitHub: claude-code-action and its security model", to the GitHub track. The lesson teaches what the action does, how it is installed, which permissions it needs, and who can start it. It then covers prompt injection, which is when a stranger hides orders in text that the AI reads, and the ways the action's docs say to limit the damage. It also shows how to pin the action to a full commit SHA, and why this repo chose not to run it for now.

The hands-on task has you write `.github/workflows/claude.yml` in your practice repo. It uses `on: issue_comment` with an `@claude` guard, a small `permissions:` block plus `github_token`, and the action pinned to a commit SHA. You install no app and add no secret. The file stays switched off. Read `content/github/gh11-claude-in-github/lesson.md` first, then `task/README.md` and `task/check.yaml`.

A few ideas to look for. A small `permissions:` block only limits Claude if you pass `github_token: ${{ secrets.GITHUB_TOKEN }}`. Otherwise the action uses the Claude app's own token. The `id-token: write` permission is only needed on that default app path. The write-access check decides who may start a run, not who wrote the text Claude reads. And the command most people try to look up a tag's SHA returns the tag object, not the commit, so you always read the `type`.

The task has five read-only `gh` checks on the practice repo. They test that the file exists, that a `uses:` line has `anthropics/claude-code-action@` and 40 hex characters, that the file has `id-token: write`, that the action is given `github_token: ${{ secrets.GITHUB_TOKEN }}`, and that no `sk-ant-` string appears (this one must answer `false`).

For reviewers:
- The brief named three source ids that are not in `content/sources.yaml`. The lesson uses the real ones (`claude-code-action-setup`, `claude-code-action-security`, `claude-code-action-examples-claude`, `claude-code-action-readme`) and I added no manifest entries.
- The two Claude Code pages are linked only. Everything taken from `docs/HARNESS.md` is marked as this repo's own note. The lesson says the sources do not state how plan limits are shared.
- I ran the first four checks with `app.checker.run_gh_checks`. As expected they all fail on `siddharth-0044/hint-kata` (no such file), on `octocat/Hello-World`, and on a repo that does not exist, each with the 404 shown.
- For the passing case I ran the same four filters with the system `jq` on 12 workflow variants: the good file, a tag, a short SHA, 41 hex characters, a missing or read-only `id-token`, `id-token: write` with a trailing comment, a hard-coded key, CRLF line endings, a quoted `uses:`, a SHA only in a comment, and the SHA of the tag object. All gave the expected answer. The tag-object SHA passes, which is a known limit of the checker.
- I also ran three of the filters through `gh`'s own jq (gojq) on `ci.yml` with the action name swapped. The `\b` and `(?m)` forms compile there, and lookahead would not.
- The fifth check, `github_token`, was added after review. I tested its regex with the system `jq` on a file with and without the line, but not through `run_gh_checks`.
- The SHA `34968b5981d5d170904281aa3df6f3c0d4a28855` is the commit behind release `v1.0.249`, the newest on 2026-10-14, and the commit the cached sources were pinned to.
- I did not run the action or the workflow, so what `contents: read` stops and what a failed run looks like are expectations, not facts.

Closes #97

🤖 Generated with [Claude Code](https://claude.com/claude-code)
