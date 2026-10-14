This PR adds the "Watch it run" player: a lesson page can replay a recorded run one step at a time. The player pauses at a "what happens next?" question and only shows the explanation after you pick an answer. The answers stay on the server: `public_view()` removes them before the trace is sent to the browser, and a separate POST route checks your choice. Two scripts in `traces/scripts/` make the recordings. `agent_run.py` runs a small Pydantic AI agent against `FunctionModel` (a scripted fake model, so no API key or network), walks it with `agent.iter`, and turns the messages into steps, including a `ModelRetry`. `pr_timeline.py` reads a real pull request through `gh api` and keeps only short summaries. The loader finds `trace.json` under the `content_root` setting. Read `app/traces.py` first, then `traces/scripts/agent_run.py`.

Closes #10

🤖 Generated with [Claude Code](https://claude.com/claude-code)
