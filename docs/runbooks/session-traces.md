# Runbook: turn a Claude Code session into a lesson trace

Raw transcripts never enter the repo. Only the reviewed, normalised `trace.json` is committed.

## 1. Pick a session
Any finished session works (`claude --from-pr N` is not required). Transcripts live at
`~/.claude/projects/<project>/<session-id>.jsonl` and are deleted after 30 days. If the SessionEnd hook is
enabled (`docs/HARNESS.md` section 3), a copy is in `~/hint-kata-inbox/`.

## 2. Normalise
```
uv run python traces/scripts/claude_session.py \
  --transcript ~/hint-kata-inbox/<session-id>.jsonl \
  --repo SiddharthMuramkar/hint-kata --pr 23 \
  --title "Building the trace player" \
  --out content/github/<lesson>/trace.json
```
`--repo/--pr` are optional: they append the GitHub side (commits, checks, review, merge). The script keeps only
user text, assistant text, tool calls and short tool results, and masks paths, emails and secret shapes.

## 3. Review by hand (hard gate)
Open the JSON and check every step:
- [ ] No secrets or tokens (search for `[redacted]` and read around each one).
- [ ] No personal paths, names, hostnames or emails.
- [ ] No third-party content (other people's code, messages or private repo text).
- [ ] Delete noisy steps. Add an `annotation` (why + citations) to the steps that teach something.
- [ ] Fill `objectives` and `takeaways`. Add `checkpoint` questions by hand.
- [ ] Set `source.redaction.human_reviewed` to `true`.

## 4. Commit through a PR
Branch, add `content/github/<lesson>/trace.json`, open a PR. Never commit the `.jsonl`.
