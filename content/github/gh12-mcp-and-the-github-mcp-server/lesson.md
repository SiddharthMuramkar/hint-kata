---
id: gh12-mcp-and-the-github-mcp-server
track: github
title: "MCP and the GitHub MCP server"
minutes: 25
pins:
  gh: "2.95"
  claude-code: "2.1.296"
  mcp-spec: "2026-07-28"
  github-mcp-server: "c59e8c1"
sources:
  - mcp-docs-intro
  - mcp-docs-architecture
  - mcp-docs-security-best-practices
  - github-mcp-server-install-claude
  - github-mcp-server-remote-server
  - github-pull-requests-concepts-helping-others-review-your-changes
  - claude-code-docs-mcp
---
Up to now, every GitHub action in this track went through you: you typed `git` and `gh` commands, or you clicked in the browser. This lesson is about a different door. A coding agent can reach GitHub through a standard plug called MCP. You will learn what MCP is, what the GitHub MCP server gives an agent, how to connect it to Claude Code without leaking a token, and what the repo's rules still do when an agent is the one opening the pull request. At the end you do the whole loop once: an issue, an agent-made pull request, a review, a merge. This site is not affiliated with GitHub, Anthropic or the MCP project. It teaches how these tools work and links to the official pages.

Three questions run through the lesson. Who talks to whom? What is the agent allowed to do? Who is still accountable for the merge?

## What MCP is

MCP stands for Model Context Protocol. It is an open standard that lets an AI application connect to things outside itself: files, databases, search tools, other services. ([What is MCP?](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro))

The docs compare it to a USB-C port. Before USB-C, each gadget needed its own cable. With one agreed plug, any device fits any socket. MCP does the same job for AI applications. Without it, every AI app would need its own custom code for every service. With it, a service builds one MCP server, and any app that speaks MCP can use it.

Why does that matter to you? Because "GitHub for agents" does not have to be built again inside each agent. One GitHub server, many agents. It also means that what the agent can do is decided by the server and by how you connect it, which is the part you control.

One more point from the docs: MCP only defines how the two sides exchange context. It says nothing about how the AI uses a model or what it does with the answer. ([Architecture overview](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture))

## Host, client and server

MCP has three roles. ([Architecture overview: participants](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture))

- The **host** is the AI application you use, for example Claude Code.
- The **client** is a small part inside the host. The host makes one client for each server it connects to, and each client keeps its own connection.
- The **server** is the program that provides context or tools.

So if Claude Code is connected to GitHub and to a filesystem tool, it holds two clients, one for each. You do not write the client. You only decide which servers to connect.

"Server" does not mean a machine in a data centre. It means the program, wherever it runs. The docs describe two kinds, depending on how the two sides are joined:

- **Local, over stdio.** The host starts the server as a program on your own computer and talks to it through its standard input and output. Such a server usually serves a single client.
- **Remote, over Streamable HTTP.** The server runs somewhere else, and the client sends it web requests. One remote server can serve many clients. Remote servers use normal web sign-in, such as a bearer token in a header. MCP recommends OAuth for getting that token.

The messages themselves are JSON-RPC, the same in both cases. You will not read them by hand. What you will remember is the choice: a local server is code that runs on your machine, and a remote server is code someone else runs for you. That choice matters for security, and the security section comes back to it.

## What a server can offer

A server can expose three kinds of thing, called primitives. ([Architecture overview: primitives](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture))

- **Tools** are actions the AI may call: create a file, query a database, call an API.
- **Resources** are data the AI may read for context: file contents, records, responses.
- **Prompts** are reusable templates that help shape a conversation with the model.

The client finds out what is on offer by asking. For tools, it sends a `tools/list` request, reads the answer, and then calls the one it wants with `tools/call`. So the list is not fixed in the client. A server can change its tools, and the host sees the new list.

For GitHub, the tools are the interesting part: read an issue, read a pull request, read a file, create a branch, open a pull request. The agent picks a tool by its name and its description, and the server does the work with whatever token you gave it. The agent has no powers of its own on GitHub. It has exactly the powers of the token.

## The GitHub MCP server

GitHub publishes an MCP server. It comes in two forms. ([Remote GitHub MCP Server](https://github.com/github/github-mcp-server/blob/c59e8c199efbf14467211861de44afaeeb6873e3/docs/remote-server.md), [Install in Claude applications](https://github.com/github/github-mcp-server/blob/c59e8c199efbf14467211861de44afaeeb6873e3/docs/installation-guides/install-claude.md))

- **Remote.** GitHub hosts it at `https://api.githubcopilot.com/mcp/`. Nothing to install. You send your token in an `Authorization` header.
- **Local.** You run it yourself, as a Docker image (`ghcr.io/github/github-mcp-server`) or as a downloaded program. It can sign you in through OAuth in the browser, or take a personal access token. If you give it both, the token wins.

The older npm package `@modelcontextprotocol/server-github` is marked deprecated as of April 2025. Do not start from old tutorials that use it.

The server groups its tools into **toolsets**, such as `repos`, `issues`, `pull_requests`, `actions` and `git`. You can turn on only the groups you need. On the remote server you do it in the address, or with headers:

| What you want | How, on the remote server |
| --- | --- |
| Read-only tools | add `/readonly` to the end of the address, or send the header `X-MCP-Readonly: true` |
| Only one toolset | use the address `/x/<toolset>`, for example `/x/issues` |
| A few toolsets | send the header `X-MCP-Toolsets`, for example `repos,issues` |
| A hand-picked list of tools | send the header `X-MCP-Tools`, for example `get_file_contents,issue_read,pull_request_read` |

Two small behaviours are worth knowing. A wrong toolset name is silently ignored, so the server starts with fewer tools than you thought. A wrong tool name in `X-MCP-Tools` is an error and the server does not start. When something looks missing, check the spelling first.

There is also a **lockdown** switch (`X-MCP-Lockdown`). In lockdown mode, the server hides the content of public issues written by people who have no push access to the repo. The docs call it a best-effort content filter and say it is not a security boundary. Keep that wording in mind for the security section: it tells you the filter is a help, not a wall.

## Connect it to Claude Code

The install page for Claude Code has one command for the remote server. You run it in your terminal, not inside a Claude Code session. ([Install in Claude applications](https://github.com/github/github-mcp-server/blob/c59e8c199efbf14467211861de44afaeeb6873e3/docs/installation-guides/install-claude.md)) Here is a version that is read-only and that takes the token from an environment variable instead of typing it in the command:

```bash
export GITHUB_PAT="$(grep '^GITHUB_PAT=' .env | cut -d '=' -f2-)"
claude mcp add-json github '{"type":"http","url":"https://api.githubcopilot.com/mcp/readonly","headers":{"Authorization":"Bearer '"$GITHUB_PAT"'"}}'
```

The first line reads a line `GITHUB_PAT=...` from a local `.env` file. The second line registers a server called `github`. The page says this `add-json` form is for Claude Code 2.1.1 and newer, and gives an older `claude mcp add --transport http` form for earlier versions. On Windows the `add-json` command can answer `Invalid input` for an HTTP server. If you see that, use the older form.

After you add the server, restart Claude Code. Then check it:

```bash
claude mcp list
claude mcp get github
```

Inside a session, the `/mcp` command shows the same servers. If tools do not appear, the page suggests checking the JSON syntax, restarting, and running Claude Code from the project folder, so the settings apply to that project.

**Scopes decide who sees the server.** The `--scope` flag has three values:

- `local` is the default. Only you, only in this project.
- `project` shares the server with everyone through a file named `.mcp.json` in the project.
- `user` makes it available to you in every project.

Read the second one again. If you add a server with `--scope project` and the token is inside the command, the token lands in `.mcp.json`. That file is meant to be committed. The install page itself suggests adding `.env` and `.mcp.json` to `.gitignore`. A token in a public repo is a leaked token, and GH5 told you what to do next: revoke it first, clean up after.

Claude Code has its own long page on MCP. This site does not copy it. It is linked here, with a short summary in our own words: it covers how to add servers of each kind, where the settings live, and how the tools show up in a session. Read it when you need details beyond the install page: [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp).

## Keep the agent on a short leash

An MCP server is a way to give an agent real power over your account. Treat the connection like a key you hand to a very fast, very literal helper. Five habits keep it safe.

**1. Give the token the fewest rights that still work.** The MCP security page describes the attack on a broad token: if one leaks, whoever holds it can reach everything it covers, and revoking it breaks all your workflows at once. Its remedy is to start with a small set of low-risk rights and widen only when a task needs more. ([Security best practices: scope minimization](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)) For GitHub, that means a fine-grained token that names only the one repo you are working on, with read access to start. The install page's troubleshooting hints talk about a `repo` scope, which is for classic tokens. A classic token is not tied to one repository. Prefer the narrower kind.

**2. Start read-only.** The `/readonly` address and the `X-MCP-Readonly` header remove every tool that changes something. An agent that can only read cannot open a pull request by mistake. Switch to write tools only for a task that needs them, then switch back. Narrow toolsets help in the same way.

**3. Keep the token out of files you share.** See the scopes above. Use the default `local` scope for a token. Keep `.env` and `.mcp.json` out of git. This repo's own rule is that secrets never go in `.mcp.json`. A server there would use `${VAR}` references that are filled in from your environment.

**4. Read the command before you run a local server.** The MCP security page warns about local servers: a server is a program that runs with the same rights as the app that started it. A bad startup command in a config can run anything, such as copying your files out or deleting them. The page says a client should show you the exact command and ask before it runs one. ([Security best practices: local MCP server compromise](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)) So when a tutorial gives you a `docker run ...` or an `npx ...` line, read every word and know where the image or package comes from. A remote server avoids that risk, but it means you trust whoever runs it with the data you send.

**5. Remember that the agent reads text written by other people.** Anyone can open an issue on a public repo, and the agent will read it as part of its job. That text can contain instructions meant for the agent and not for you. The lockdown switch above exists for this reason, and the docs say it is not a boundary. This lesson's own advice: do not let the agent act on a stranger's issue without you reading it first, and do not give it write tools while it does.

One more rule from the same page is for people who build servers. A server must refuse tokens that were not issued to it, and must not pass on a client's token to another service. ([Security best practices: token passthrough](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)) The reason is that the server's controls and audit trail stop meaning anything if tokens flow around it. You only need the idea here: a token belongs to one service, for one purpose.

## An agent pull request under the ruleset

Now join this to the rest of the track. Say the agent can read your issues and has a way to push a branch and open a pull request. What stops it from doing damage? Your ruleset from GH8. The agent has the rights of your token, but `main` has its own rules.

On this repo, `gh api repos/SiddharthMuramkar/hint-kata/rules/branches/main --jq '[.[].type]'` printed `["deletion","non_fast_forward","pull_request","required_status_checks"]` on 2026-10-15. In words: `main` cannot be deleted, cannot be force-pushed, can only change through a pull request, and the required check must pass first. An agent cannot push straight to `main`, and it cannot get around the `checks` run. A person's token is held to the same rules, which is the point.

The loop for an agent-assisted change has these steps:

1. **An issue states the job.** Small, one goal, in plain words. It also gives the agent a number to refer to.
2. **The agent reads the issue** through the MCP server, with read-only tools.
3. **The agent works on its own branch,** never on `main`. A name such as `issue-12-fix-typo` ties the branch to the issue.
4. **It opens a pull request** whose description ends with a closing keyword and the issue number, for example `Closes #12`. GitHub's docs say to use closing keywords when a pull request should close an issue after merging. ([Helping others review your changes](https://docs.github.com/en/pull-requests/concepts/helping-others-review-your-changes)) On 2026-10-15 `gh issue list --state closed --json number,stateReason,closedByPullRequestsReferences` showed issue 133 with state reason `COMPLETED` and pull request 134 as its closer. That is the keyword at work.
5. **The required checks run.** Green means the tests passed. It does not mean the change is right.
6. **A person reviews.** Use the five questions from GH10: size, scope, tests, secrets, and whether the text explains itself.
7. **A person merges,** with the squash method your ruleset allows. The merge closes the issue.

Notice where the agent's part ends. It writes, branches and proposes. The decision to merge stays with you, and the ruleset makes that a rule, not a habit. The agent is a fast helper in the middle of a flow whose guard rails are the same as before. That is the main idea of this lesson.

## How Hint Kata does it

This repo does not use the GitHub MCP server. That is a decision, written down in `docs/HARNESS.md`. Its list of rejected items says the GitHub MCP server "duplicates `gh`; needs a PAT". The `gh` command line tool is already signed in on the machine and covers everything the build needs, so adding a second door to the same house would only mean another token to guard. The repo's `.mcp.json` holds `{"mcpServers": {}}` on purpose, and `HARNESS.md` repeats the rule that secrets never go in that file.

The flow is the one in the previous section, done with `gh`. Each task is an issue. The builder works on a branch named like `issue-98-lesson-gh12`, in its own worktree. It opens a pull request whose body ends with `Closes #98`, and the ruleset `protect-main` requires the pull request and the `checks` run. A reviewer reads the diff, and the merge is a squash. Read `.claude/rules/git.md` for the exact rules.

So is MCP pointless here? No. It is a good fit when a tool has no `gh` equivalent, or when you want the same connection in several agents. The honest test is the one `HARNESS.md` used: does the server give the agent something that the tools already in place do not? If the answer is no, the cheapest and safest choice is not to add it.

Now do it once yourself. The task page walks you through connecting the GitHub server read-only to Claude Code, writing an issue, letting an agent open a pull request for it, reviewing and merging it yourself, and cleaning up the token. **Check my work** reads your pull requests and your issues.

Adapted from the Model Context Protocol documentation, [What is MCP?](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro), [Architecture overview](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture) and [Security Best Practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices), version 2026-07-28, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Modified: summarized and adapted. Adapted from [github/github-mcp-server](https://github.com/github/github-mcp-server) (commit c59e8c1, pages `docs/remote-server.md` and `docs/installation-guides/install-claude.md`), © 2025 GitHub, MIT License. Adapted from GitHub Docs, © GitHub, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Modified: summarized and adapted. Read 2026-10-15. Checked with `gh` 2.95 and Claude Code 2.1.296. This site is not affiliated with GitHub, Anthropic or the MCP project.

**Sources:**
[What is MCP?](https://modelcontextprotocol.io/docs/2026-07-28/getting-started/intro),
[Architecture overview](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture),
[Security Best Practices](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices),
[Remote GitHub MCP Server](https://github.com/github/github-mcp-server/blob/c59e8c199efbf14467211861de44afaeeb6873e3/docs/remote-server.md),
[Install GitHub MCP Server in Claude Applications](https://github.com/github/github-mcp-server/blob/c59e8c199efbf14467211861de44afaeeb6873e3/docs/installation-guides/install-claude.md),
[Helping others review your changes](https://docs.github.com/en/pull-requests/concepts/helping-others-review-your-changes).

**Linked, not reproduced (no reuse licence):**
[Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp).
