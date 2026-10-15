## What changed

Lesson GH12, "MCP and the GitHub MCP server", is a new lesson in the GitHub track. It teaches what MCP is (host, client and server, local over stdio and remote over HTTP, and the tools, resources and prompts a server offers), what the GitHub MCP server gives an agent, how to connect it to Claude Code, and how to do that safely. Then it joins everything: an agent-made pull request from issue to merge under the ruleset from GH8.

- `lesson.md` has eight sections, from "What MCP is" to "How Hint Kata does it". The last one is honest: this repo does not use the GitHub MCP server, because `gh` already covers the job (see `docs/HARNESS.md`).
- Six quiz items, two think-deeper questions and a two-question warm-up.
- The task has you make a read-only, one-repo token, connect the server to Claude Code, write an issue, let an agent open a pull request that ends with `Closes #<n>`, review it, and merge it yourself. Then you remove the token.
- `check.yaml` has four read-only `gh` checks: a merged pull request into `main` that closes an issue, a closed issue with a pull request as its closer, a pull request rule still on `main`, and no `.mcp.json` or `.env` committed.

## Why

An agent has exactly the powers of its token, and the ruleset still decides what a pull request must pass. A beginner should learn both halves together. The lesson is written from the cached MCP docs (CC BY 4.0) and the github-mcp-server pages (MIT). The Claude Code MCP page is linked only, with a short summary in our own words. All sources were already in `content/sources.yaml`, so the manifest is unchanged.

## Checked

The content validators pass. The checker has no starter or solution folder for this track, so I ran the four checks against this repo (the three pull request checks pass; the fourth fails because this repo really has an `.mcp.json`) and against an unrelated repo, where the first three fail. Tests, ruff, format and ty all pass.

Read first: `content/github/gh12-mcp-and-the-github-mcp-server/lesson.md`, section "Keep the agent on a short leash".

Closes #98

🤖 Generated with [Claude Code](https://claude.com/claude-code)
