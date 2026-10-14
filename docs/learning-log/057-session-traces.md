This PR adds a way to turn a real Claude Code session into a lesson trace for the GitHub track. `traces/scripts/claude_session.py` reads the session's JSONL transcript line by line and keeps only a short whitelist: your prompts, Claude's text, tool calls and short tool results. Claude Code's transcript format is internal and changes between versions, so the script skips anything it does not recognise and never crashes on a bad line. Before anything is stored, a redaction step rewrites home paths to `~`, removes emails and masks common secret shapes. The output is a draft: `human_reviewed` stays `false` until a person checks it using `docs/runbooks/session-traces.md`. A small `SessionEnd` hook copies transcripts to `~/hint-kata-inbox/` so they survive the 30-day cleanup; it is not enabled yet, and `docs/HARNESS.md` has the snippet. Read `traces/scripts/claude_session.py` first.

Closes #57

🤖 Generated with [Claude Code](https://claude.com/claude-code)
