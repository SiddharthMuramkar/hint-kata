# Claude Code features and harness research

_Research archive. Checked against primary sources on 2026-10-14. Facts about fast-moving tools (Claude Code, Pydantic AI, FastAPI, GitHub, OpenRouter) go stale quickly: re-check before relying on a number._

- **Needed by:** Phase 1 (harness)
- **Licence / attribution notes:** Claude Code docs are © Anthropic, all rights reserved; this file paraphrases and links, it does not copy them.
- **Covers:** subagents, skills, saved workflows, /goal, /loop, output styles, hooks, settings, permissions, sandbox, MCP, CLAUDE.md, rules, worktrees, GitHub Action, plugins, model routing, auto mode

## Claude Code docs: subagents, skills, saved workflows, /goal, /loop, background agents, agent teams, output styles (checked 2026-10-14 at code.claude.com; local CLI is v2.1.296)

**Summary.** I read each page as raw Markdown from code.claude.com/docs/en/*.md, found through llms.txt. Every docs page can be fetched this way, which is handy for the RAG docs re-sync. Subagents are .claude/agents/*.md files: YAML frontmatter, with the Markdown body used as the system prompt. Only name and description are required. Field names are camelCase (disallowedTools, permissionMode, maxTurns), and a field Claude Code doesn't recognize is skipped without any error. Skills are .claude/skills/<name>/SKILL.md files. Every field is optional and the names are kebab-case (allowed-tools, disable-model-invocation, user-invocable). Custom commands have been merged into skills: a .claude/commands/x.md file and a skill both create /x. Saved workflows are .claude/workflows/<name>.js scripts. The file must start with a literal `export const meta = { name, description }` block, and the body uses agent()/pipeline()/parallel()/phase()/log() and a global `args`. You get one by pressing `s` in /workflows to save a run, then run it as /<name>. /goal sets a completion condition (up to 4,000 characters). After each turn a small fast model reads the transcript and judges it met, not yet met, or impossible. There is no built-in turn cap, so you add 'or stop after N turns' to the condition yourself. /loop is a bundled skill with the form `/loop [interval] [prompt]`. With an interval it runs on a fixed cron schedule; without one Claude picks the gap itself (1 min to 1 h). Fixed loops expire after 7 days, and loops only fire while the session is open. There are five output styles: Default, Proactive, Concise, Explanatory and Learning. Learning does insert `TODO(human)` markers in the code and then waits for you to write that part. Set it per project with "outputStyle": "Learning", which is case-sensitive. Output styles do not apply to non-fork subagents. The installed CLI (2.1.296) meets every version requirement on these pages; the newest is v2.1.295.

### Findings

- **Subagent files live in .claude/agents/ (project, priority 3) or ~/.claude/agents/ (user, priority 4). Above them are managed settings (1) and the --agents CLI JSON (2); plugin agents/ is lowest (5). Each file is YAML frontmatter between --- markers, followed by a Markdown body that becomes the system prompt. Only name and description are required.** [high, load-bearing]
  Directories are scanned recursively, and identity comes only from the `name` field; the filename doesn't have to match. A name can't contain ':', start with '-', or exceed 256 characters. A file with no name is treated as documentation and skipped silently, and a name without a description is skipped with only a debug-log entry. Edits are hot-reloaded, but the first file in an agents/ directory that didn't exist at session start needs a restart. `claude plugin validate .claude/agents` checks that the frontmatter parses. The body replaces the Claude Code system prompt; it is not appended to it.
  Source: <https://code.claude.com/docs/en/sub-agents.md>
- **These are all the subagent frontmatter fields: name, description, tools, disallowedTools, model, permissionMode, maxTurns, skills, mcpServers, hooks, memory, background, omitClaudeMd, effort, isolation, color, initialPrompt, experimental (whose only key is cacheTtl). Names are camelCase, and Claude Code ignores any field it doesn't recognize without reporting an error.** [high, load-bearing]
  Accepted values. model: sonnet|opus|haiku|fable|<full model ID>|inherit. permissionMode: default|acceptEdits|auto|dontAsk|bypassPermissions|plan, with manual as an alias for default. memory: user|project|local. effort: low|medium|high|xhigh|max. isolation: worktree. color: red|blue|green|yellow|purple|orange|pink|cyan. experimental.cacheTtl: 5m|1h. Plugin subagents ignore hooks, mcpServers and permissionMode. The --agents JSON form accepts the same fields with `prompt` in place of the body, but not color or experimental. If the main session runs in bypassPermissions, acceptEdits or auto, the subagent's permissionMode is ignored.
  Source: <https://code.claude.com/docs/en/sub-agents.md>
- **Tool restriction: `tools` is an allowlist (comma-separated string or YAML list) and `disallowedTools` is a denylist. disallowedTools is applied first, then tools is resolved against what remains. An entry with a specifier such as Bash(git push *) removes the whole tool. To block particular commands, use permissions.deny in settings instead.** [high, load-bearing]
  Leaving out `tools` gives the subagent every tool available to subagents, MCP tools included. `mcp__<server>` or `mcp__<server>__*` matches a whole server, and `mcp__*` in disallowedTools removes all MCP tools. These tools are always removed: AskUserQuestion, EnterPlanMode, ExitPlanMode (unless permissionMode is plan), ScheduleWakeup, WaitForMcpServers, Workflow and EndConversation, plus Agent once the depth limit is reached. Background subagents keep only Read, Grep, Glob, LSP, Bash, PowerShell, Edit, Write, NotebookEdit, WebFetch, WebSearch, TodoWrite, Skill, ToolSearch, EnterWorktree, ExitWorktree, Monitor, TaskStop, SendMessage and Artifact, plus all MCP tools. If no `tools` entry resolves to a real tool, the launch usually fails.
  Source: <https://code.claude.com/docs/en/sub-agents.md>
- **There are four ways to invoke a subagent: (1) automatic delegation based on `description` (adding 'use proactively' encourages it); (2) naming it in natural language; (3) an @-mention like `@"code-reviewer (agent)"` or `@agent-<name>`, which guarantees that agent runs; (4) running the whole session as that agent with `claude --agent <name>` or "agent": "<name>" in .claude/settings.json.** [high]
  From v2.1.198 on, /agents only prints a reminder to ask Claude or edit the files. The older interactive wizard is gone. Combined subagent descriptions above 15,000 tokens trigger a startup warning. Claude can resume a finished subagent with SendMessage, but the built-in Explore and Plan agents are one-shot and can't be resumed.
  Source: <https://code.claude.com/docs/en/sub-agents.md>
- **Foreground vs background: in interactive sessions 'fork mode' is on by default, so every subagent Claude spawns runs in the background and Claude can't request the foreground. When fork mode is off (-p and the Agent SDK), Claude backgrounds by default and uses the foreground only when it needs the result before continuing.** [high]
  Foreground subagents block the conversation and pass permission prompts through to you. Background subagents surface their prompts in the main session and name the subagent asking. `background: true` keeps a subagent in the background. CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1 forces the foreground. Ctrl+B sends a running task to the background, and /tasks lists them. Limits: 20 concurrent subagents (CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS) and nesting up to 3 layers deep (CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH). CLAUDE_CODE_FORK_SUBAGENT=0 turns fork mode off. /subtask <task> starts a fork that inherits the full conversation.
  Source: <https://code.claude.com/docs/en/sub-agents.md>
- **A non-fork subagent starts with a fresh context: its own system prompt, the delegation message, every CLAUDE.md level, a git status snapshot and any preloaded skills. It does not get your output style, auto memory or conversation history.** [high, load-bearing]
  The Explore and Plan agents skip CLAUDE.md and git status, and `omitClaudeMd: true` skips CLAUDE.md for your own agents. The `memory` field gives an agent a persistent directory: ~/.claude/agent-memory/<name>/ for user, .claude/agent-memory/<name>/ for project (the recommended scope), or .claude/agent-memory-local/<name>/ for local. The first 200 lines or 25KB of MEMORY.md is injected, and Read/Write/Edit are enabled automatically. `skills:` preloads the full content of up to 32 skills, but not skills marked disable-model-invocation.
  Source: <https://code.claude.com/docs/en/sub-agents.md>
- **Skill format: a .claude/skills/<skill-name>/SKILL.md file (project), ~/.claude/skills/<skill-name>/SKILL.md (personal), or <plugin>/skills/<name>/SKILL.md (plugin, invoked as /plugin:name). It has YAML frontmatter and a Markdown body. All fields are optional; description is recommended.** [high, load-bearing]
  The frontmatter is read only if `---` is the first line of the file. Unparseable YAML still loads the skill, with no fields set. In the skill listing, description plus when_to_use is truncated at 1,536 characters. The docs advise keeping SKILL.md under 500 lines and moving reference material into supporting files. Don't name a folder `synced` or `anthropic-skills`. /reload-skills rescans the directories, and /skills lists and toggles skills. Claude Code skills follow the Agent Skills open standard (agentskills.io).
  Source: <https://code.claude.com/docs/en/skills.md>
- **These are all the skill frontmatter fields: name, description, when_to_use, argument-hint, arguments, disable-model-invocation, user-invocable, allowed-tools, disallowed-tools, model, effort, context (fork), agent, background, hooks, paths, shell (bash|powershell), metadata, license, compatibility. Names are kebab-case, except when_to_use.** [high, load-bearing]
  Unknown fields are ignored without an error. Booleans also accept yes/no/on/off/1/0. `model` and `effort` apply only for the current turn. `background` matters only with context: fork; it defaults to true. `paths` uses globs to limit when the skill auto-activates. The casing differs between file types: subagents use disallowedTools, skills use disallowed-tools.
  Source: <https://code.claude.com/docs/en/skills.md>
- **Invocation control: by default both you and Claude can invoke a skill. `disable-model-invocation: true` means only you can, and its description is left out of Claude's context. `user-invocable: false` means only Claude can. `allowed-tools` pre-approves tools only for the turn that invoked the skill; it does not restrict which tools are available.** [high, load-bearing]
  A skill runs directly only when /name is at the start of your message. Written after other text, it only gives Claude permission to run it. allowed-tools takes effect even in untrusted folders in -p runs, so review repo skills before running Claude Code there. claude.ai uploads and the Skills API accept only name, description, license, compatibility, metadata and allowed-tools; any other key, e.g. argument-hint, fails with an 'Unexpected key(s)' error. Permission rules can target skills with Skill(name) or Skill(name *).
  Source: <https://code.claude.com/docs/en/skills.md>
- **Custom commands have been merged into skills: .claude/commands/deploy.md and .claude/skills/deploy/SKILL.md both create /deploy and behave the same. Command files accept the same frontmatter except `name` and `paths`. Skills are the recommended format for new work.** [high]
  A command in a subdirectory gets a namespace: .claude/commands/frontend/component.md becomes /frontend:component. For a skill, the command name is the frontmatter `name` or the directory name. The .claude directory page says the same: 'Commands and skills are now the same mechanism'.
  Source: <https://code.claude.com/docs/en/skills.md>
- **Skill arguments: $ARGUMENTS is the full string, $ARGUMENTS[N] or $N is 0-based and shell-quoted, and $name maps to the `arguments` frontmatter list. If no placeholder receives the arguments, Claude Code appends 'ARGUMENTS: <value>'. A line starting with !`cmd` (or a ```! block) runs before Claude sees the skill, and its output is inlined.** [high]
  Other substitutions: ${CLAUDE_SKILL_DIR}, ${CLAUDE_PROJECT_DIR}, ${CLAUDE_SESSION_ID}, ${CLAUDE_EFFORT}. If an injected command exits non-zero, the whole skill invocation aborts; exit code 1 from search/diff-type commands is exempt. Injected commands never prompt for permission: anything not allowed aborts, unless you pre-approve it in allowed-tools. Up to 6 skills can be stacked, as in /write-tests /fix-issue 123.
  Source: <https://code.claude.com/docs/en/skills.md>
- **`context: fork` runs the skill in a new subagent of the `agent` type: Explore, Plan, general-purpose (the default), or a custom agent from .claude/agents. It is not a fork of your conversation, so it starts without your history. It runs in the background unless you set `background: false`.** [high]
  Use it only for skills with explicit task instructions. A skill that holds only guidelines comes back with nothing useful. A forked skill running in the background gets the reduced background tool set, and its edits fall outside checkpoints, so /rewind can't undo them. With agent: Explore, none of your CLAUDE.md files load.
  Source: <https://code.claude.com/docs/en/skills.md>
- **Saved workflows are .js files in .claude/workflows/ (project, shared via git) or ~/.claude/workflows/ (personal). You don't write them from scratch: you save a run with `s` in /workflows, and the file then runs as /<name>. The file must open with `export const meta = { name, description }` as a plain object literal, with an optional `phases` array.** [high, load-bearing]
  The body is plain JavaScript with top-level await. Available calls: agent(prompt, {schema, label, stallMs}), pipeline(items, fn), parallel(), phase(title), log(), and the `args` global. If meta contains anything other than literals, /<name> disappears from autocomplete. Date.now(), Math.random() and a no-argument new Date() throw, and import() fails. To edit a saved file, run /workflow-authoring first, then /reload-skills. A project workflow beats a personal one with the same name, and plugin workflows run as /plugin:name.
  Source: <https://code.claude.com/docs/en/workflows.md>
- **Workflow args: you invoke a saved workflow in plain language, e.g. 'Run /triage-issues on issues 1024, 1025, and 1030'. Claude passes the input as structured JSON into the script's global `args`, which is undefined if nothing was passed. The tool's inputs are script | name | scriptPath, plus args and resumeFromRunId.** [high, load-bearing]
  Availability: all paid plans, but on Pro you must turn on Dynamic workflows in /config. Pro defaults to the `small` size guideline (fewer than 5 agents); other plans default to medium (fewer than 10). Runtime limits: 16 concurrent agents by default, fewer on machines with fewer CPUs; 1,000 agents per run; 4,096 items per parallel() or pipeline() call. A 'Large workflow' warning appears above 25 agents or 1.5M projected tokens. Before each run you approve a plan in manual mode. Workflows can be disabled with "disableWorkflows": true or CLAUDE_CODE_DISABLE_WORKFLOWS=1. Source for the plan and limit details: https://code.claude.com/docs/en/workflows.md
  Source: <https://code.claude.com/docs/en/agent-sdk/typescript.md>
- **`/goal <condition>` sets a single session-scoped completion condition (up to 4,000 characters) and starts working immediately. After every turn a small fast model reads the condition and the transcript and returns not-yet-met (keep going), met (goal cleared) or impossible (cleared and marked failed). `/goal` alone shows status; `/goal clear` (or stop, off, reset, none, cancel) removes it.** [high]
  The evaluator calls no tools and judges only what appears in the transcript, so the condition must be something Claude's own output can prove, e.g. 'npm test exits 0'. There is no built-in turn limit; add 'or stop after 20 turns' to the condition. /goal doesn't change your permission mode, so use auto mode if you want it unattended. It stops early if Claude makes no tool calls for several turns. It clears on errors you have to fix: auth failure, no credits, context overflow, or an unavailable model. Evaluation is skipped while background work is running. It is internally a session-scoped prompt-based Stop hook, so it needs workspace trust and is unavailable when disableAllHooks or allowManagedHooksOnly is set. It also works with -p, e.g. `claude -p "/goal ..."`.
  Source: <https://code.claude.com/docs/en/goal.md>
- **`/loop [interval] [prompt]` is a bundled skill, also available as /proactive. With an interval (s/m/h/d, rounded to cron's one-minute granularity) it runs on a fixed schedule. Without an interval, Claude picks a delay of 1 minute to 1 hour after each run. With no prompt it runs .claude/loop.md, then ~/.claude/loop.md, then a built-in maintenance prompt.** [high]
  Stopping: press Esc to cancel a self-paced loop's next run, or Claude ends it with ScheduleWakeup stop:true. Fixed-interval loops keep going until you cancel them through CronList/CronDelete or until the 7-day expiry. Tasks fire only while the session is open and idle, missed runs aren't made up, and a session holds at most 50 tasks. Recurring tasks are deliberately started a bit late (jitter), by up to 30 minutes. A self-paced loop isn't restored on --resume. CLAUDE_CODE_DISABLE_CRON=1 turns scheduling off. A loop only runs skills Claude is allowed to invoke itself. For schedules that must run without an open session, the docs point to Routines, Desktop scheduled tasks or GitHub Actions.
  Source: <https://code.claude.com/docs/en/scheduled-tasks.md>
- **Background agents: `claude agents` opens 'agent view' (research preview), and `claude --bg "prompt"` starts a background session directly. `claude --agent <name> --bg "..."` runs one of your custom subagents as that session's main agent. You manage sessions with claude attach/logs/stop <id>.** [high]
  Each background session uses your subscription quota on its own, so ten sessions use it about ten times as fast. Sessions run locally and survive sleep but not shutdown. A session can fail to start with a 'possibly low memory' note, and when memory is low the supervisor stops idle sessions. /fork copies the conversation into a new background session, while /subtask creates a forked subagent whose result returns to the current conversation.
  Source: <https://code.claude.com/docs/en/agent-view.md>
- **Agent teams are experimental and off by default. Turn them on with env CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 in settings.json. A lead session coordinates teammates through a shared task list and direct messages.** [high]
  With teams enabled, any subagent Claude gives a name launches as a teammate, so teams can form without you asking. Teams need an interactive session; -p is not supported. The default display mode is in-process; split panes need tmux or iTerm2 and don't work in VS Code's integrated terminal. Limitations: one team per session, no nested teams, the lead can't change, in-process teammates aren't restored on /resume, and token usage is much higher.
  Source: <https://code.claude.com/docs/en/agent-teams.md>
- **Output styles: besides Default there are four built-in styles: Proactive, Concise, Explanatory and Learning. Learning adds the same '★ Insight' blocks as Explanatory. When Claude reaches a real design decision, it writes a `TODO(human)` comment into the file, posts a '● Learn by Doing' request (Context / Your Task / Guidance), and then stops and waits for you to write that code.** [high, load-bearing]
  Claude still writes routine code itself. You fill in the TODO(human), tell Claude you're done, and it replies with one Insight about your code before continuing. A style is an instruction Claude follows, not something enforced. To guarantee a behavior, use a hook. Explanatory and Learning produce more output tokens than Default.
  Source: <https://code.claude.com/docs/en/output-styles.md>
- **To set a style for a project, put "outputStyle": "Learning" in a settings file. The value is case-sensitive: a non-matching value such as "learning" silently gives you Default. The /output-style command and the /config menu write to .claude/settings.local.json, which is not shared, so for a committed project default put it in .claude/settings.json.** [high, load-bearing]
  Precedence, highest first: managed, then --settings, then .claude/settings.local.json, then .claude/settings.json, then ~/.claude/settings.json (https://code.claude.com/docs/en/settings.md). A style switched mid-session applies from your next message (v2.1.251+); the /output-style command needs v2.1.269+. In VS Code, open the / command menu and choose Output styles. Custom styles go in .claude/output-styles/*.md with frontmatter name, description, keep-coding-instructions (default false) and force-for-plugin. Style files are read at startup, so restart after editing one. Styles reach forks but not other subagents.
  Source: <https://code.claude.com/docs/en/output-styles.md>
- **Every Claude Code docs page is available as raw Markdown at code.claude.com/docs/en/<page>.md, indexed by https://code.claude.com/docs/llms.txt. That makes these docs easy to ingest for the track 3 RAG re-sync.** [high]
  I fetched all the pages above with curl -sL on the .md URLs. Some pages contain MDX/JSX components (for example claude-directory.md embeds a React explorer) that would need stripping before chunking. The pages are long (sub-agents.md is about 108KB, skills.md about 107KB) and are full of 'Requires vX / Before vY' notes that change often.
  Source: <https://code.claude.com/docs/llms.txt>
- **The locally installed Claude Code is 2.1.296, which is at or above every version requirement on these pages; the newest is v2.1.295 (forked skills invoked inside workflows).** [high]
  Checked with the read-only command `claude --version`, which printed '2.1.296 (Claude Code)'. Requirements checked include /output-style (v2.1.269), workflow usage-limit pause (v2.1.271), omitClaudeMd (v2.1.271), /subtask (v2.1.212) and the per-invocation subagent effort parameter (v2.1.292).
  Source: <https://code.claude.com/docs/en/skills.md>

### Exact snippets (copied from the sources named)

**Subagent file (.claude/agents/code-reviewer.md), minimal format** — <https://code.claude.com/docs/en/sub-agents.md>

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. When invoked, analyze the code and provide
specific, actionable feedback on quality, security, and best practices.
```

**User-only skill with pre-approved git tools (SKILL.md frontmatter)** — <https://code.claude.com/docs/en/skills.md>

```yaml
---
name: commit
description: Stage and commit the current changes
disable-model-invocation: true
allowed-tools: Bash(git add *) Bash(git commit *) Bash(git status *)
---
```

**Forked skill with dynamic context injection (PR summary via gh)** — <https://code.claude.com/docs/en/skills.md>

```yaml
---
name: pr-summary
description: Summarize changes in a pull request
context: fork
agent: Explore
allowed-tools: Bash(gh *)
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`
- Changed files: !`gh pr diff --name-only`

## Your task
Summarize this pull request...
```

**Saved workflow script (.claude/workflows/*.js) with meta block** — <https://code.claude.com/docs/en/workflows.md>

```javascript
export const meta = {
  name: 'audit-routes',
  description: 'Audit every route handler for missing auth checks',
}

const found = await agent('List every .ts file under src/routes/.', {
  schema: { type: 'object', required: ['files'], properties: { files: { type: 'array', items: { type: 'string' } } } },
})

const audits = await pipeline(found.files, file =>
  agent(`Audit ${file} for missing authentication checks.`, { label: file }),
)

return audits.filter(Boolean)
```

**Set output style in a settings file (use "Learning" for this project; value is case-sensitive)** — <https://code.claude.com/docs/en/output-styles.md>

```json
{
  "outputStyle": "Explanatory"
}
```

**Custom output style file (.claude/output-styles/*.md)** — <https://code.claude.com/docs/en/output-styles.md>

```markdown
---
name: Diagrams first
description: Lead every explanation with a diagram
keep-coding-instructions: true
---

When explaining code, architecture, or data flow, start with a Mermaid diagram showing the structure, then explain in prose.

## Diagram conventions

Use `flowchart TD` for control flow and `sequenceDiagram` for request paths. Keep diagrams under 15 nodes.
```

**Default /loop prompt (.claude/loop.md)** — <https://code.claude.com/docs/en/scheduled-tasks.md>

```markdown
Check the `release/next` PR. If CI is red, pull the failing job log,
diagnose, and push a minimal fix. If new review comments have arrived,
address each one and resolve the thread. If everything is green and
quiet, say so in one line.
```

**What the Learning style's TODO(human) handoff looks like** — <https://code.claude.com/docs/en/output-styles.md>

```text
● Learn by Doing

Context: The upload form is in place and calls validateFile() before accepting a file. Size and type checks work for images, but the switch statement has no handling for documents yet.

Your Task: In upload.js, implement the case "document" branch inside validateFile(). Look for TODO(human).

Guidance: Decide on a size limit for documents and whether the file extension has to match the MIME type. Return {valid: boolean, error?: string}.
```

### Recommendations
- Put "outputStyle": "Learning" (exact casing) in the committed .claude/settings.json of the learning-site repo. /output-style writes only to .claude/settings.local.json, which is personal and not shared.
- Write subagent frontmatter in camelCase (disallowedTools, permissionMode, maxTurns) and skill frontmatter in kebab-case (allowed-tools, disable-model-invocation). Both file types ignore misspelled fields without an error, so after adding one, check that it loaded with /skills, /tasks or `claude --debug`.
- Create new slash commands as .claude/skills/<name>/SKILL.md, not .claude/commands/, for example /new-lesson <track> <slug> and /resync-docs. Add disable-model-invocation: true to anything with side effects, such as git push or DB writes.
- Add 1-2 read-only project subagents: a pr-reviewer with tools: Read, Grep, Glob, Bash and model: sonnet or haiku, and a lesson-fact-checker. Give them memory: project if you want their learnings committed. These are also good examples for the GitHub track's 'Claude Code in a PR flow' lessons.
- Use /goal for bounded, checkable tasks and always include a stated check plus a turn cap, e.g. `/goal pytest -q exits 0 and ruff check is clean; no test files modified; or stop after 15 turns`.
- Use /loop only for short in-session polling, such as `/loop 10m check CI on my PR`. Run the scheduled docs re-sync in GitHub Actions with a `schedule` trigger: /loop dies with the session and recurring loops expire after 7 days.
- On a Mac with limited RAM and probably a Pro plan, leave agent teams off. Keep workflowSizeGuideline at small, and consider lowering CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS and CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS in the settings env.
- For track 3 RAG, ingest code.claude.com/docs/en/*.md (indexed by llms.txt). Strip the MDX/JSX components, and store a fetched-at date and the CLI version next to each chunk, because the version notes change every few releases.

### Risks
- Unknown or misspelled frontmatter fields in subagents, skills and output styles are dropped without an error. Mixing camelCase and kebab-case (e.g. disallowed-tools in an agent file) quietly removes the restriction you thought you set.
- The outputStyle value is case-sensitive in settings files: "learning" falls back to Default without any warning.
- Output styles don't reach non-fork subagents, and in interactive sessions subagents run in the background by default. Work Claude delegates won't follow the Learning style, so no TODO(human) markers appear in code written by subagents or workflow agents.
- Learning style waits for you at each TODO(human), while /goal keeps starting turns on its own. The docs don't describe how the two interact (it's possible the evaluator judges 'not yet met' and continues on its own). This is unverified.
- /goal's evaluator sees only the transcript and runs no commands, so it can be convinced by claimed results. It has no hard turn cap unless you write one into the condition.
- Skill allowed-tools applies even in untrusted folders in -p runs. A cloned repo's skills can pre-approve broad Bash access.
- Workflows, background sessions (claude --bg) and agent teams each multiply quota use. Background sessions can fail with 'possibly low memory' on a low-RAM Mac.
- These docs change quickly; nearly every section carries 'Requires vX / Before vY' notes. Lesson content and RAG chunks will go stale unless they're pinned to a CLI version and re-synced.

### Open questions
- Which Claude plan is the learner on? On Pro, Dynamic workflows must be turned on in /config and the workflow size guideline defaults to small.
- Should the Learning style be committed for everyone who clones the repo (.claude/settings.json), or kept personal (.claude/settings.local.json)?
- How does the Learning style's stop-and-wait at TODO(human) behave inside an active /goal loop or a self-paced /loop? Not documented; needs a hands-on test.
- Does the workflow `meta` block accept fields beyond name, description and phases? The public page mentions only these; the bundled /workflow-authoring skill may document more, but I didn't read it.
- Should track 3 cover agent teams at all, given they are experimental and change how named subagents behave once enabled?

### Fact-check (second agent re-read the sources)

I checked against the live code.claude.com docs on 2026-10-14: sub-agents.md, skills.md, workflows.md, output-styles.md, settings.md, scheduled-tasks.md and agent-sdk/typescript.md. All 11 claims hold. Minor omissions and imprecisions:
1. Plugin subagents also ignore initialPrompt.
2. Background subagents can also keep SubagentHandback.
3. omitClaudeMd still loads managed policy CLAUDE.md files.
4. The skill `effort` field is not documented as lasting only for the current turn.
5. WorkflowInput also has `title` and `description` fields, which the tool ignores.
The only snippet problem is the outputStyle snippet: its label says Learning but its value is Explanatory. The other 7 snippets match the official examples character for character.

Snippet checks:
- Subagent file (code-reviewer.md): none. It matches the docs exactly.
- User-only commit skill: none. It matches the docs exactly, and a space-separated allowed-tools value is valid.
- pr-summary forked skill: none. It matches the docs exactly.
- Saved workflow audit-routes.js: none. It matches the docs exactly.
- outputStyle settings JSON: the keys are valid, but the label says to use "Learning" for this project while the snippet sets "Explanatory". Change the value to "Learning" (case-sensitive) or fix the label.
- Custom output style 'Diagrams first': none. It matches the docs exactly.
- .claude/loop.md: none. It matches scheduled-tasks.md exactly.
- Learning style 'Learn by Doing' block: none. It matches the docs exactly.

## Claude Code hooks, settings, permissions and sandboxing (code.claude.com docs, verified 2026-10-14, latest CLI 2.1.299)

**Summary.** I checked the current Claude Code docs (hooks, hooks-guide, settings, settings-reference, permissions, sandboxing, tools-reference) and the CHANGELOG. The newest CLI on npm is 2.1.299. Hooks now cover 33 events and 5 handler types: command, http, mcp_tool, prompt, and agent (agent is experimental). They live in settings.json as hooks -> Event -> [{matcher, hooks:[handler]}]. Command handlers have a newer exec form ("command" plus an "args" array, added in v2.1.139) and an onFailure:"block" option (v2.1.295 or later). onFailure matters because hooks fail open by default: exit 1, a crash or a timeout lets the action through. There are two ways to block a PreToolUse call: exit 2 with the reason on stderr, or exit 0 and print hookSpecificOutput.permissionDecision "deny" plus permissionDecisionReason. PostToolUse cannot undo a tool call, but it can give Claude lint errors through a top-level {"decision":"block","reason":...}, through hookSpecificOutput.additionalContext, or through exit 2 with stderr. Three things changed from older guides. MultiEdit is now a "legacy" tool. Glob and Grep are off by default on macOS, so Claude searches with Bash find/grep. A Read deny rule now also blocks Bash cat/head/tail/sed/tee and redirects on that path, but not `grep -r pattern .` or a Python script that opens the file. Only the OS sandbox (Seatbelt on macOS) covers those cases. The sandbox merges Read deny rules into its own read block, but it does not cover the Read/Edit tools, hooks or MCP servers. Settings precedence is managed > --settings > .claude/settings.local.json > .claude/settings.json > ~/.claude/settings.json. Array keys and hooks merge across levels, and a deny rule at any level wins. I tested the logic of the three hook scripts below by piping sample JSON into them: secret guard, git-push guard and ruff post-edit. I have not run them inside a live Claude Code session.

### Findings

- **Hook events, 33 in total: SessionStart, Setup, UserPromptSubmit, UserPromptExpansion, PreToolUse, PermissionRequest, PermissionDenied, PostToolUse, PostToolUseFailure, PostToolBatch, Notification, MessageDisplay, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, Stop, StopFailure, TeammateIdle, InstructionsLoaded, ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, PreModelSwitch, PostModelSwitch, Elicitation, ElicitationResult, SessionEnd.** [high, load-bearing]
  Matchers are ignored silently on events without matcher support (UserPromptSubmit, Stop, PostToolBatch, CwdChanged, etc.). Tool events match on tool_name. PreToolUse/PostToolUse do not fire for EndConversation.
  Source: <https://code.claude.com/docs/en/hooks.md>
- **Settings schema: {"hooks": {"<Event>": [{"matcher": "...", "hooks": [ {handler} ]}]}}. Fields on every handler: type (required), if, timeout (seconds), statusMessage, once (honored only in skill frontmatter). Command handler fields: command (required), args, async, asyncRewake, shell ("bash"|"powershell"), onFailure ("continue"|"block").** [high, load-bearing]
  Default timeouts: 600s for command/http/mcp_tool (30s on UserPromptSubmit/PreModelSwitch/PostModelSwitch, 10s on MessageDisplay), 30s for prompt, 60s for agent. SessionEnd hooks share a 1.5s budget. All matching hooks run in parallel, and identical handlers are deduplicated. 'if' takes one permission-rule pattern such as "Bash(git *)" and works only on tool events. The docs call it best-effort and say to use permissions, not 'if', for hard allow/deny.
  Source: <https://code.claude.com/docs/en/hooks.md>
- **Five handler types: "command", "http" (POSTs the JSON to url, with headers plus allowedEnvVars), "mcp_tool" (server, tool, input with ${tool_input.file_path} substitution), "prompt" (prompt with $ARGUMENTS, optional model) and "agent" (experimental subagent verifier).** [high, load-bearing]
  An HTTP hook cannot block with a status code. It must return 2xx with a JSON decision body. Non-2xx responses and connection failures are non-blocking unless onFailure is "block".
  Source: <https://code.claude.com/docs/en/hooks.md>
- **Matcher syntax: "*", "" or an omitted matcher matches everything. A matcher made only of letters, digits, _, -, spaces, commas and | is an exact name or a list of exact names ("Edit|Write"). Anything else is an unanchored JavaScript regex, so "Edit.*" also matches NotebookEdit. Matchers are case-sensitive. An MCP matcher needs "mcp__server__.*".** [high, load-bearing]
  Source: <https://code.claude.com/docs/en/hooks.md>
- **${CLAUDE_PROJECT_DIR} is a path placeholder and is also exported as an env var to hooks. In exec form ("command":"python3","args":["${CLAUDE_PROJECT_DIR}/.claude/hooks/x.py"]) no shell runs and nothing needs quoting. Without args, the command runs through sh -c and you should write "$CLAUDE_PROJECT_DIR" in double quotes.** [high, load-bearing]
  The args field (exec form) was added in v2.1.139 (CHANGELOG https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md). In a worktree, CLAUDE_PROJECT_DIR keeps pointing at the original project root, while the input field 'cwd' follows Claude's cd and worktree changes.
  Source: <https://code.claude.com/docs/en/hooks.md>
- **stdin JSON for PreToolUse has session_id, prompt_id, transcript_path, cwd, scratchpad_dir, permission_mode, hook_event_name, tool_name, tool_input, tool_use_id (plus agent_id/agent_type inside subagents). tool_input per tool: Bash {command, description, timeout, run_in_background}; Write {file_path, content}; Edit {file_path, old_string, new_string, replace_all}; Read {file_path, offset, limit}. PostToolUse adds tool_response and duration_ms.** [high, load-bearing]
  For Read/Edit/Write, file_path is always absolute: ~ and relative paths are expanded before the hook runs. On Windows it uses backslashes, so normalize separators before comparing. Grep input: pattern, path, glob, output_mode. Glob input: pattern, path. Agent input: prompt, description, subagent_type, model.
  Source: <https://code.claude.com/docs/en/hooks.md>
- **MultiEdit is no longer in the tools reference. The permissions page calls it 'the legacy MultiEdit tool', and its path rules are never consulted. On macOS, Linux and WSL, Glob and Grep are left out of the default tool set, so Claude searches with Bash find/grep (built-in bfs/ugrep), and hooks and permission rules see those searches as Bash calls.** [high, load-bearing]
  A secret guard on a Mac must inspect Bash commands, not only the Read/Grep tools. Use Edit(...) path rules instead of Write(...)/MultiEdit(...)/NotebookEdit(...) (https://code.claude.com/docs/en/permissions.md).
  Source: <https://code.claude.com/docs/en/tools-reference.md>
- **How blocking works. Exit 0 = success, and stdout is parsed as JSON only if the whole output is a single JSON object. Exit 2 = blocking error: stderr becomes the reason Claude sees, and JSON cannot override it. Any other exit code without valid JSON = non-blocking error, so the action continues. The JSON route is exit 0 plus {"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"..."}}.** [high, load-bearing]
  permissionDecision accepts allow, deny, ask or defer (defer works only in -p mode). When several hooks answer, deny > defer > ask > allow. Top-level decision/reason ('approve'/'block') is deprecated for PreToolUse. Fields at the wrong level are ignored without any error (debug log line: 'Hook JSON output had unrecognized keys'). If your shell profile echoes text, the JSON is no longer parsed. The docs warn that exit 1 does NOT block: use exit 2 to enforce a policy.
  Source: <https://code.claude.com/docs/en/hooks.md>
- **Hooks fail open by default: a missing script, a crash (exit 1), invalid JSON or a timeout lets the tool call continue. Setting "onFailure": "block" on a command or http hook makes those failures block. It requires Claude Code v2.1.295 or later, and the latest npm version is 2.1.299.** [high, load-bearing]
  onFailure has no effect on Stop/SubagentStop/TaskCompleted/TeammateIdle or on async hooks. The SchemaStore JSON schema does not yet list onFailure (I checked https://json.schemastore.org/claude-code-settings.json), so VS Code will flag it. The docs say schema lag is expected.
  Source: <https://code.claude.com/docs/en/hooks.md>
- **PostToolUse can feed lint errors back to Claude in several ways. A top-level {"decision":"block","reason":"..."} adds the reason next to the tool result. hookSpecificOutput.additionalContext arrives as a system reminder. updatedToolOutput replaces what Claude sees. Exit 2 shows stderr to Claude. PostToolUse cannot undo the tool call.** [high, load-bearing]
  Claude never sees stderr from a hook that exits 0. additionalContext, systemMessage and plain stdout are each capped at 10,000 chars, and longer output is saved to a file with a 2,000-char preview. A PostToolUse hook matching Edit|Write does not fire when a Bash command such as sed -i rewrites the file. FileChanged covers that case but cannot block.
  Source: <https://code.claude.com/docs/en/hooks.md>
- **A PreToolUse deny is enforced in every permission mode, including bypassPermissions/--dangerously-skip-permissions and dontAsk. A hook 'allow' cannot override deny or ask rules from settings. An installed mod handling tool.check can override a non-managed hook's block.** [high]
  A hook that exits 2 stops the call before allow rules are evaluated, so the docs suggest pairing a broad 'Bash' allow with hook-based blocks (https://code.claude.com/docs/en/permissions.md).
  Source: <https://code.claude.com/docs/en/hooks-guide.md>
- **Settings files: ~/.claude/settings.json (user), .claude/settings.json (shared project, commit it), .claude/settings.local.json (personal for the project; git-excluded when Claude Code creates it) and managed settings (managed-settings.json, MDM or server-managed). Precedence, highest first: managed > --settings CLI JSON > local > project > user.** [high, load-bearing]
  Array keys such as permissions.allow/deny merge across files instead of overriding. Hooks from all levels merge too. A deny at any level beats an allow at any level. disableAllHooks follows normal precedence, so a project false overrides a user true, and it cannot disable managed hooks. Cloud sessions do not read ~/.claude/settings.json. Hook edits are now picked up by a file watcher (older guides said hooks were snapshotted at startup).
  Source: <https://code.claude.com/docs/en/settings.md>
- **Permission rule syntax is Tool or Tool(specifier), evaluated deny, then ask, then allow; the first match wins. Bash uses wildcards: Bash(git push *). The legacy trailing ':*' still works as an equivalent (Bash(git push:*) == Bash(git push *)), but only at the end of a pattern. Rules apply per subcommand across && || ; | & and newlines, and common wrappers (timeout, nice, nohup, bare xargs) are stripped.** [high, load-bearing]
  The docs list what a Bash rule does not catch: Bash(git push *) does not stop 'git -C . push origin main', 'git -c push.default=current push', "git 'push' origin main", /usr/bin/git, or sh -c '...'. Bare-tool deny rules ('Bash') remove the tool from Claude's context. Tool(param:value) works for deny/ask only, and not on primary fields such as command/file_path.
  Source: <https://code.claude.com/docs/en/permissions.md>
- **Read/Edit rules use gitignore syntax. '//path' is an absolute path. '~/path' is relative to home. '/path' is relative to the settings source (the project root for .claude/settings.json, but ~/.claude for user settings). 'path' or './path' is relative to cwd. A bare filename matches at any depth (Read(.env) == Read(**/.env)), and a '!' entry in the same deny list carves out exceptions.** [high, load-bearing]
  Gotcha: Read(/secrets/**) in USER settings blocks ~/.claude/secrets, not the project's secrets folder. A '!' carve-out only cancels rules from the same source. A Read deny also blocks Edit and Write on the same path (v2.1.208+/2.1.228+), but not NotebookEdit.
  Source: <https://code.claude.com/docs/en/permissions.md>
- **A Read deny rule DOES stop Bash 'cat .env' today. Read/Edit deny rules apply to Bash file commands Claude Code recognizes (cat, head, tail, sed, tee), to redirect targets (> file, < file), to @-mentions and to IDE selection context. They do NOT apply to commands that read files without naming them ('grep -r pattern .') or to subprocesses such as python/node scripts that open files.** [high, load-bearing]
  For OS-level enforcement the docs say to enable the sandbox. .claudeignore has no effect. ignorePatterns is deprecated and replaced by permissions.deny.
  Source: <https://code.claude.com/docs/en/settings-reference.md>
- **Sandbox settings: sandbox.enabled, failIfUnavailable, autoAllowBashIfSandboxed (default true), excludedCommands, allowUnsandboxedCommands, filesystem.{allowWrite,denyWrite,denyRead,allowRead,disabled}, network.{allowedDomains,deniedDomains,...} and credentials.{files,envVars}. On macOS it uses Seatbelt. It is off by default. Turn it on with /sandbox, which writes to .claude/settings.local.json, or set it in settings.** [high, load-bearing]
  Defaults: writes allowed only to cwd, temp and added dirs. Reads are allowed across most of the machine, INCLUDING ~/.ssh and ~/.aws/credentials. Network allowedDomains starts empty. Read(...) deny rules are merged into sandbox denyRead. The sandbox wraps Bash, PowerShell and Monitor only. Read/Edit/WebFetch, hooks, MCP servers and statusLine run outside it. Claude can retry a command with dangerouslyDisableSandbox; set allowUnsandboxedCommands:false to disable that. Sandbox path prefixes differ from permission rules: '/tmp/x' is absolute and './x' is project-relative.
  Source: <https://code.claude.com/docs/en/sandboxing.md>
- **Useful keys. "$schema": "https://json.schemastore.org/claude-code-settings.json". env: an object of strings that overrides shell exports, applied from project/local settings only after workspace trust. permissions.defaultMode: default|acceptEdits|plan|auto|dontAsk|bypassPermissions|manual (auto and bypassPermissions are ignored from project/local settings). outputStyle: e.g. "Explanatory" or "Learning". attribution {commit, pr, sessionUrl} or false. statusLine {type:"command", command, padding, refreshInterval, hideVimModeIndicator}.** [high, load-bearing]
  includeCoAuthoredBy has been deprecated since v2.0.62 and is ignored once attribution.commit or attribution.pr is set. attribution:false needs v2.1.281 or later, and earlier versions reject the whole settings file. Built-in output styles are Default, Proactive, Concise, Explanatory and Learning (https://code.claude.com/docs/en/output-styles.md). Learning fits this learner audience.
  Source: <https://code.claude.com/docs/en/settings-reference.md>
- **Workspace trust: in interactive sessions, hooks from every settings file (even ~/.claude) are held back until you accept the trust dialog. In -p and SDK sessions the folder counts as trusted, so a cloned repo's committed .claude/settings.json hooks run immediately.** [high]
  For -p runs on repos you didn't write, use --bare, --setting-sources user or --settings '{"disableAllHooks": true}'. Worth teaching in the GitHub track: a malicious PR can add hooks.
  Source: <https://code.claude.com/docs/en/hooks.md>
- **PreToolUse never fires for files added with @-mentions in the prompt, so only a Read deny rule blocks those. Hooks run outside the sandbox with your full user access and with no TTY.** [high]
  Source: <https://code.claude.com/docs/en/hooks.md>
- **Anthropic's official hook examples: protect-files.sh (PreToolUse on Edit|Write, exits 2 on .env, package-lock.json or .git/) and a Prettier PostToolUse example. Reference validator: examples/hooks/bash_command_validator_example.py in anthropics/claude-code (fetched, HTTP 200).** [high]
  The official protect-files example does substring matching on file_path only, so it would not catch Bash 'cat .env'. That is why the project needs a Bash-aware guard.
  Source: <https://code.claude.com/docs/en/hooks-guide.md>
- **Checked on this Mac: macOS ships jq (/usr/bin/jq, jq-1.7.1-apple). /usr/bin/python3 is 3.9.6, while the uv-managed python3 on PATH is 3.14. Type hints like 'str | None' raise TypeError on 3.9 unless the script has 'from __future__ import annotations'.** [medium, load-bearing]
  I ran sw_vers/which/python3 --version locally (macOS 26.6.2, ruff 0.17.0, uv 0.13.0). If Claude Code starts with a PATH that lacks ~/.local/bin (for example from a GUI-launched VS Code), 'python3' resolves to 3.9.6. With onFailure:block, a crashing guard would then block every Bash call. The scripts below include the __future__ import and were tested on 3.9.6 and 3.14.
  Source: <https://code.claude.com/docs/en/hooks-guide.md>
- **Debugging: /hooks opens a read-only browser of your hooks. 'claude --debug' writes a debug log with full stderr and 'Hook output does not start with {' lines. Ctrl+O opens the transcript view. Test a script by piping sample JSON into it: echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | ./hook.sh; echo $?** [high]
  Source: <https://code.claude.com/docs/en/hooks-guide.md>

### Exact snippets (copied from the sources named)

**Hooks settings schema (exact docs example: PostToolUse on Edit|Write)** — <https://code.claude.com/docs/en/hooks.md>

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/lint-check.sh"
          }
        ]
      }
    ]
  }
}
```

**Decision outputs (exact from docs): PreToolUse deny, top-level block (PostToolUse/Stop/etc.), exit-2 script** — <https://code.claude.com/docs/en/hooks.md>

```text
// PreToolUse: exit 0 and print
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Database writes are not allowed"
  }
}

// PostToolUse / Stop / UserPromptSubmit etc.: top-level decision
{
  "decision": "block",
  "reason": "Test suite must pass before proceeding"
}

// PostToolUse additionalContext
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "This file is generated. Edit src/schema.ts and run `bun generate` instead."
  }
}

# Exit-code style (bash)
#!/bin/bash
# Reads JSON input from stdin, checks the command
input=$(cat)
command=$(jq -r '.tool_input.command' <<<"$input")

if [[ "$command" == rm* ]]; then
  echo "Blocked: rm commands are not allowed" >&2
  exit 2  # Blocking error: tool call is prevented
fi

exit 0  # No decision: the normal permission flow applies
```

**permissions.deny for sensitive files (exact docs example)** — <https://code.claude.com/docs/en/settings-reference.md>

```json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Read(./config/credentials.json)",
      "Bash(curl *)"
    ]
  }
}
```

**sandbox block (exact docs example; put in ~/.claude/settings.json or .claude/settings.local.json)** — <https://code.claude.com/docs/en/settings-reference.md>

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "excludedCommands": ["docker *"],
    "filesystem": {
      "allowWrite": ["/tmp/build", "~/.kube"],
      "denyRead": ["~/.aws/credentials"]
    },
    "network": {
      "allowedDomains": ["github.com", "*.npmjs.org"]
    }
  }
}
```

**(a) .claude/hooks/protect_secrets.py: PreToolUse guard for secret files (file tools + Bash). Logic tested with piped JSON; not docs-copied** — <https://code.claude.com/docs/en/hooks.md>

```python
#!/usr/bin/env python3
"""PreToolUse guard: deny file tools and Bash commands that touch secrets.
Fails closed: any crash denies the call."""
from __future__ import annotations

import fnmatch
import json
import re
import sys

SECRET_NAMES = [
    ".env", ".env.*", "*.pem", "*.key", "*.p12", "*.pfx",
    "id_rsa*", "id_ed25519*", "id_ecdsa*", ".netrc", ".pgpass",
    "secrets.*", "credentials.json", "service-account*.json",
]
SECRET_DIRS = {"secrets", ".secrets", ".ssh", ".aws"}
SAFE_NAMES = {".env.example", ".env.sample", ".env.template"}


def is_secret(path: str) -> bool:
    parts = [p for p in path.replace("\\", "/").split("/") if p]
    if not parts:
        return False
    name = parts[-1].lower()
    if name in SAFE_NAMES:
        return False
    if any(p.lower() in SECRET_DIRS for p in parts[:-1]):
        return True
    return any(fnmatch.fnmatch(name, pat) for pat in SECRET_NAMES)


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def main() -> None:
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    ti = data.get("tool_input") or {}
    if tool == "Bash":
        cmd = ti.get("command", "")
        # split on whitespace, quotes, shell operators: cat<.env, "./.env", $(cat .env)
        for tok in re.split(r"[\s;&|<>()`'\"=,]+", cmd):
            if tok and is_secret(tok):
                deny(f"Blocked: command touches secret file '{tok}'. "
                     "Ask the user for the value instead.")
        sys.exit(0)
    for key in ("file_path", "notebook_path", "path", "pattern", "glob"):
        val = ti.get(key)
        if isinstance(val, str) and val and is_secret(val):
            deny(f"Blocked: {tool} on secret path '{val}' is not allowed.")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail closed
        deny(f"protect_secrets hook error, blocking to be safe: {exc}")

# Tested: denies Read /p/.env, Edit certs/server.pem, 'cat .env | grep KEY',
# 'x=$(cat ./.env.local)', 'sed -n 1p<.env', Read ~/.ssh/config;
# allows .env.example, main.py, 'uv run pytest'. NOT caught (by design gap):
# python -c "open('.e'+'nv')", grep -r KEY .
```

**(b) .claude/hooks/guard_git_push.py: PreToolUse guard against pushing to main/master and force-pushing (exit 2 + stderr). Logic tested; not docs-copied** — <https://code.claude.com/docs/en/hooks.md>

```python
#!/usr/bin/env python3
"""Block git push to main/master, force pushes, --all/--mirror, deleting main,
and bare `git push` / `git push origin HEAD` while on main/master."""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys

PROTECTED = {"main", "master"}
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def block(msg: str) -> None:
    print(f"Blocked by git-push guard: {msg} Push a feature branch and open a PR.",
          file=sys.stderr)
    sys.exit(2)


def current_branch(cwd: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def dest_branch(refspec: str) -> str:
    return refspec.lstrip("+").split(":")[-1].removeprefix("refs/heads/")


def check_segment(tokens: list[str], cwd: str) -> None:
    try:
        i = next(k for k, t in enumerate(tokens) if os.path.basename(t) == "git")
    except StopIteration:
        return
    rest, j = tokens[i + 1:], 0
    while j < len(rest) and rest[j].startswith("-"):  # git global options
        if rest[j] == "-C" and j + 1 < len(rest):
            cwd = os.path.join(cwd, rest[j + 1])
        j += 2 if rest[j] in GIT_OPTS_WITH_VALUE else 1
    if j >= len(rest) or rest[j] != "push":
        return
    args = rest[j + 1:]
    flags = [a for a in args if a.startswith("-")]
    positionals = [a for a in args if not a.startswith("-")]
    for f in flags:
        if f in ("--force", "--mirror", "--all", "--force-if-includes") or \
           f.startswith("--force-with-lease") or \
           (not f.startswith("--") and "f" in f[1:]):
            block(f"'{f}' (force/mirror/all push) is not allowed.")
        if f in ("-d", "--delete") and any(dest_branch(p) in PROTECTED for p in positionals[1:]):
            block("deleting main/master is not allowed.")
    refspecs = positionals[1:]  # positionals[0] is the remote
    for r in refspecs:
        if r.startswith("+"):
            block(f"force refspec '{r}' is not allowed.")
        if dest_branch(r) in PROTECTED:
            block(f"refspec '{r}' targets a protected branch.")
    if not refspecs or any(dest_branch(r) in ("HEAD", "@") for r in refspecs):
        branch = current_branch(cwd)
        if branch in PROTECTED:
            block(f"you are on '{branch}', so this push would update it.")


def main() -> None:
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command", "")
    if not re.search(r"\bgit\b", cmd) or not re.search(r"\bpush\b", cmd):
        sys.exit(0)
    cwd = data.get("cwd") or os.getcwd()
    for seg in re.split(r"&&|\|\||[;|&\n()`]", cmd):
        try:
            tokens = shlex.split(seg)
        except ValueError:
            tokens = seg.split()
        check_segment(tokens, cwd)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail closed
        print(f"git-push guard crashed, blocking to be safe: {exc}", file=sys.stderr)
        sys.exit(2)

# Tested (exit 2): git push origin main | origin HEAD:main | -f origin x |
# --force-with-lease | -uf origin x | origin +x | origin x:refs/heads/master |
# git push (on main) | origin HEAD (on main) | git -C ../repo-on-main push |
# npm test && git push origin main | /usr/bin/git push origin main | --all |
# origin --delete master. Allowed (exit 0): git push -u origin feature-branch,
# bare git push on a feature branch, git commit -m 'push to main later'.
```

**(c) .claude/hooks/ruff_after_edit.py: PostToolUse format + lint, sends remaining errors back to Claude. Skip paths tested; ruff concise output checked** — <https://code.claude.com/docs/en/hooks.md>

```python
#!/usr/bin/env python3
"""PostToolUse: run `uv run ruff format` + `uv run ruff check --fix` on the edited
.py file; if errors remain, return decision=block + reason so Claude fixes them."""
from __future__ import annotations

import json
import os
import subprocess
import sys


def run(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["uv", "run", "--quiet", *args], cwd=cwd,
                          capture_output=True, text=True, timeout=60)


def main() -> None:
    data = json.load(sys.stdin)
    path = (data.get("tool_input") or {}).get("file_path", "")
    if not path.endswith((".py", ".pyi")) or not os.path.isfile(path):
        sys.exit(0)
    project = os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()

    run(["ruff", "format", path], project)
    res = run(["ruff", "check", "--fix", "--output-format", "concise", path], project)
    if res.returncode == 0:
        sys.exit(0)
    report = (res.stdout + res.stderr).strip()[:8000]  # stay under 10k cap
    print(json.dumps({
        "decision": "block",
        "reason": f"ruff found problems it could not auto-fix in {path}:\n{report}\n"
                  "Fix these before moving on.",
    }))
    sys.exit(0)


if __name__ == "__main__":
    main()
```

**Project .claude/settings.json that wires (a), (b) and (c) together with deny rules (my composition; field names checked against the docs)** — <https://code.claude.com/docs/en/hooks.md>

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "deny": [
      "Read(**/.env)",
      "Read(**/.env.*)",
      "Read(!.env.example)",
      "Read(**/*.pem)",
      "Read(**/*.key)",
      "Read(**/secrets/**)",
      "Edit(/.claude/settings*.json)",
      "Edit(/.claude/hooks/**)"
    ],
    "ask": ["Bash(git push *)"]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write|NotebookEdit|Grep|Glob|Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3",
            "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/protect_secrets.py"],
            "timeout": 10,
            "onFailure": "block"
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3",
            "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/guard_git_push.py"],
            "timeout": 10,
            "onFailure": "block"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3",
            "args": ["${CLAUDE_PROJECT_DIR}/.claude/hooks/ruff_after_edit.py"],
            "timeout": 120,
            "statusMessage": "ruff format + check"
          }
        ]
      }
    ]
  }
}
```

### Recommendations
- Use defense in depth, strongest first. (1) Turn on GitHub branch protection or a ruleset on main: required PR, required checks, no force push. This is the only control a local Claude session cannot get around. (2) Add permissions.deny Read(...) rules for secrets, which also cover cat/head/tail/sed, redirects, @-mentions and IDE context. (3) Add the PreToolUse hooks (a) and (b) for clear error messages and better coverage of Bash variants. (4) Optionally enable the sandbox, which turns Read deny rules into an OS-level read block for every Bash subprocess.
- Pin Claude Code to 2.1.295 or later (`claude update`; npm latest is 2.1.299) before you rely on "onFailure": "block". Without it, a mistyped script path or a crash lets every call through. On older versions, drop the key and keep the scripts fail-closed internally, as written.
- Use exec form ("command": "python3", "args": ["${CLAUDE_PROJECT_DIR}/..."]) for every project hook, and put `from __future__ import annotations` at the top of every Python hook. That way the hooks still work if PATH resolves to macOS /usr/bin/python3 3.9.6. If you need a pinned interpreter, use an absolute path such as ~/.local/bin/python3 in user settings.
- Before wiring each hook into settings, test it from the terminal: echo '<json>' | python3 .claude/hooks/x.py; echo $?. Then run /hooks to confirm it loaded and `claude --debug` to watch it run. The GitHub track can turn this into a hands-on lab.
- Do not use the 'if' field on security hooks. The docs call it best-effort, and Bash(git *) can miss '/usr/bin/git push'. Matching on 'Bash' and filtering inside the script is safer. Each Python process costs about 30-50ms on a Mac.
- Use Edit(...) path rules, not Write(...) or MultiEdit(...), because Claude Code never consults those. Deny Edit on .claude/settings*.json and .claude/hooks/** so Claude cannot quietly weaken its own guardrails. These paths are already protected and prompt in every mode except bypassPermissions.
- For a beginner, set permissions.defaultMode to "default" or "acceptEdits" (never bypassPermissions), set outputStyle "Learning" or "Explanatory", and add "ask": ["Bash(git push *)"] so every push gets a human look.
- The ruff hook only sees Edit/Write. Add a CI step (`uv run ruff format --check . && uv run ruff check .`) in GitHub Actions to catch files that Bash, sed or the user changed. Optionally add a Stop hook that runs ruff on the whole repo; a Stop hook must check stop_hook_active to avoid loops.
- If you enable the sandbox on the Mac: set network.allowedDomains for pypi.org, files.pythonhosted.org, github.com, the Neon host and the Vercel API. Expect `git push` over SSH to need troubleshooting (the docs have a section on this). Consider allowUnsandboxedCommands:false only once the setup is stable.

### Risks
- Hook guards only match text. Indirect reads get past both the hook and Read deny rules: `python -c "open('.e'+'nv')"`, `uv run script.py` that loads dotenv, `grep -r KEY .`, `find . -exec cat {} +`, base64 tricks, `env`/`printenv` dumping variables already loaded into the shell, and symlinks created by Bash. Only the OS sandbox (denyRead) or keeping secrets out of the repo directory really closes this.
- The git push guard can be bypassed: `cd ../other && git push` (cwd is not tracked), variables (`git push origin $B`), aliases in ~/.gitconfig (`git p`), `git -c alias.x=push x`, `sh -c '...'`, `gh` API calls, scripts that run git, and MCP GitHub tools that push or merge directly (e.g. mcp__github__*). Treat it as a seatbelt. GitHub branch protection is the real lock.
- Hooks fail open unless onFailure is "block" (v2.1.295+). Exit 1, a timeout, invalid JSON, or a JSON field at the wrong level all mean the action proceeds, usually without a visible error.
- PreToolUse does not fire for @-mentioned files. Hooks are held until workspace trust is accepted in interactive sessions. disableAllHooks or --settings can switch them off. In bypassPermissions mode Claude can edit .claude/settings.json or the hook scripts without a prompt.
- An installed mod handling tool.check can approve a call that a non-managed PreToolUse hook blocked, and without managed settings or a Team/Enterprise plan it can also override deny rules.
- The PostToolUse ruff hook runs after the write. Reformatting changes the file under Claude, so Claude may need to re-read it before its next Edit (I did not verify how Claude Code handles this). `uv run` may sync or create .venv on first use and add seconds of latency. ruff must be in the project's dev dependencies or on PATH.
- The SchemaStore schema lags the CLI (it has no onFailure key), so VS Code will show validation warnings. A config key an older CLI doesn't recognize could invalidate the settings file; the docs show that happening for attribution:false before v2.1.281. Pin the version.
- The docs change fast. Several behaviors carry version notes (2.1.2xx), so a course that quotes them should state the CLI version it was checked against and re-check during the scheduled docs re-sync.

### Open questions
- Will the learner's Claude Code be at 2.1.295 or later when the site launches? If not, should the course leave onFailure out of the snippets?
- Does the course want Python hooks (more readable for the Pydantic/FastAPI audience) or bash+jq hooks (the official docs examples; jq ships with macOS)? Mixing both shows the two blocking styles but adds cognitive load.
- Should .env.example be readable (the carve-out above), and should Claude be allowed to create .env from it? Script (a) currently blocks `cp .env.example .env`.
- Will the sandbox be enabled for the learner's own dev setup? Network allowlisting (PyPI, GitHub SSH, Neon, Vercel) adds friction on a low-RAM Mac.
- I did not verify how Claude Code treats a file that a PostToolUse hook rewrites (stale-read errors on the next Edit). Worth testing live before teaching the ruff hook.
- Should the GitHub track also cover hooks on MCP GitHub tools (matcher "mcp__github__.*")? Those can merge or push without going through Bash. Also, plugin-bundled MCP servers use the name mcp__plugin_<plugin>_<server>__<tool>.

### Fact-check (second agent re-read the sources)

I read the current docs at code.claude.com (hooks, hooks-guide, settings, settings-reference, permissions, sandboxing, tools-reference, output-styles) with curl, plus the CHANGELOG on GitHub raw, the npm registry dist-tags and the SchemaStore schema. I also ran read-only local checks (sw_vers, jq, python3, ruff, uv, claude --version). I wrote no files. 16 of 17 claims are confirmed. Claim 15 is corrected on one point: a './x' sandbox path is relative to ~/.claude when it is in user settings. Things to flag: npm stable=2.1.287 is older than the 2.1.295 that onFailure needs (latest/next=2.1.299, installed CLI 2.1.296), and hooks-guide still tells macOS users to brew install jq even though this Mac ships /usr/bin/jq.

Corrections:
- [corrected] Sandbox keys (enabled, failIfUnavailable, autoAllowBashIfSandboxed default true, excludedCommands, allowUnsandboxedCommands, filesystem.*, network.*, credentials.{files,envVars}); Seatbelt on macOS; off by default; /sandbox writes .claude/settings.local.json; defaults; wraps Bash/PowerShell/Monitor only; sandbox path prefixes '/tmp/x' absolute, './x' project-relative. → Everything else checks out. Sandbox './x' (or no prefix) resolves to the project root only in project settings. In user settings (~/.claude/settings.json) it resolves to ~/.claude. See the 'Sandbox path prefixes' section and sandboxing.md. (<https://code.claude.com/docs/en/settings-reference.md>)

Snippet checks:
- Snippet 1 (PostToolUse Edit|Write example): none. It matches hooks.md word for word.
- Snippet 2 (decision outputs + exit-2 bash): none. All four pieces match hooks.md word for word. The // comments make it non-JSON, but it is labeled text.
- Snippet 3 (permissions.deny): none. It matches the settings-reference permissions.deny example word for word.
- Snippet 4 (sandbox block): none. It matches the settings-reference sandbox example word for word. sandbox scope is 'Any file', so the suggested placement is fine.
- Snippet 5 protect_secrets.py: output shape and input field names are correct (tool_name, tool_input.file_path/notebook_path/path/pattern/glob). Logic gaps, not doc mismatches: (1) Glob/Grep patterns such as '**/.env*' or '*.env' are not caught, because fnmatch compares the literal pattern text. (2) 'secrets.*' also matches source files such as secrets.py, and 'id_rsa*' blocks id_rsa.pub.
- Snippet 6 guard_git_push.py: exit 2 + stderr is a valid PreToolUse block, and the cwd/tool_input.command fields are correct. Logic gaps: (1) options that take a separate value (-o/--push-option, --repo, --receive-pack) shift the positionals, so 'git push -o ci.skip origin' on main skips the current-branch check. (2) sh -c/bash -c 'git push origin main' is not caught, because shlex keeps the inner string as one token.
- Snippet 7 ruff_after_edit.py: top-level decision:block + reason is the documented PostToolUse format, and file_path/cwd/CLAUDE_PROJECT_DIR are correct. Two 60s subprocess timeouts can add up to the hook's 120s timeout, and then the hook is canceled and its output discarded. An uncaught TimeoutExpired or FileNotFoundError (uv not on PATH) exits 1, which is a non-blocking error (acceptable fail-open). The documented 10k cap does not list `reason`. '--output-format concise' is valid in ruff 0.17.0.
- Snippet 8 project settings.json: every key, the nesting and the value formats are valid per hooks.md and permissions.md (exec form command+args with ${CLAUDE_PROJECT_DIR}, timeout, onFailure, statusMessage; '/'-anchored Edit rules resolve to the project root; Read(!.env.example) carves out of the earlier relative Read(**/.env.*)). Caveats: (1) onFailure is missing from the SchemaStore schema (hookCommand additionalProperties:false), so the $schema line makes VS Code flag it. (2) onFailure needs v2.1.295+, but the npm 'stable' dist-tag is 2.1.287. (3) The matcher leaves out PowerShell, which matters only where that tool is enabled.

## Claude Code docs: MCP (.mcp.json, scopes, env expansion, approvals, permissions), memory/CLAUDE.md, .claude/rules, worktrees, checkpointing, GitHub Actions, review commands, and vendor MCP entries (GitHub, Neon, Vercel, Logfire, Context7)

**Summary.** I checked everything against primary sources on 2026-10-14: code.claude.com pages found through llms.txt, the GitHub API for claude-code-action release tags, and each vendor's own MCP docs. Project MCP servers go in `.mcp.json` at the repo root under `mcpServers`. Remote entries need `"type": "http"`, because an entry with a `url` but no `type` is rejected. `${VAR}` and `${VAR:-default}` expand in `command`, `args`, `env`, `url` and `headers`, but well-known credential variables such as ANTHROPIC_API_KEY always expand to an empty string in remote `url`/`headers`. Claude Code asks for approval before using project servers in interactive sessions. That approval is recorded in `enabledMcpjsonServers` / `enableAllProjectMcpServers` / `disabledMcpjsonServers`. A cloned repo that has not been trusted cannot approve its own servers, and `claude -p`, SDK and cloud runs load project servers without asking. CLAUDE.md can live at managed, user (`~/.claude/CLAUDE.md`), project (`./CLAUDE.md` or `./.claude/CLAUDE.md`) and local (`./CLAUDE.local.md`) level. The docs recommend under 200 lines per file. `@path` imports can nest up to 4 hops, and `.claude/rules/*.md` files can be limited to certain files with `paths:` frontmatter, which is the only field rules read. Worktrees are built in: `claude --worktree <name>` (or `-w`) creates `.claude/worktrees/<name>` on branch `worktree-<name>`, and `.worktreeinclude` copies gitignored files like `.env` into it. There is no `/worktree` slash command; inside a session Claude uses the EnterWorktree tool when asked. The GitHub Action is `anthropics/claude-code-action@v1` (latest tag v1.0.249, published 2026-10-14). `/install-github-app` sets it up and stores either `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) as a repo secret. `/code-review` is now the main local review command, with `/review` as an alias since v2.1.223. `/security-review` checks the branch diff against origin's default branch, and the managed Code Review service is Team/Enterprise only. Of the vendor servers, Vercel uses OAuth only. Neon, Logfire and Context7 each support OAuth or an API key in a Bearer header. The remote GitHub server is documented with a PAT in the Authorization header and has a read-only mode, either a `/readonly` URL suffix or the `X-MCP-Readonly` header.

### Findings

- **.mcp.json format: a top-level "mcpServers" object keyed by server name. Remote entries need "type": "http" ("streamable-http" is accepted as an alias; "sse" and "ws" also exist), and an entry with a url but no type is a configuration error. stdio entries use command/args/env, with "type": "stdio" optional.** [high, load-bearing]
  Claude Code reads an entry with no type as stdio and skips it with the message 'MCP server "<name>" has a "url" but no "type"'. "type": "sdk" entries are skipped in .mcp.json. Server names may contain only letters, numbers, hyphens and underscores. The quickstart example mixes {"type":"http","url":...} and {"type":"stdio","command":"npx","args":[...]} entries (https://code.claude.com/docs/en/mcp-quickstart.md).
  Source: <https://code.claude.com/docs/en/mcp.md>
- **Transports: HTTP is the recommended transport for remote servers. SSE is deprecated; since v2.1.265 `--transport http` falls back to SSE automatically. stdio runs a local process, and everything after `--` is passed to the server untouched.** [high]
  Command forms: `claude mcp add --transport http <name> <url> [--header "Authorization: Bearer ..."]` and `claude mcp add [options] <name> -- <command> [args...]`. `--env KEY=value` must not come directly before the server name. The stdio server's environment gets CLAUDE_PROJECT_DIR, so to reference it in .mcp.json command/args you need a default: `${CLAUDE_PROJECT_DIR:-.}`. WebSocket supports neither OAuth nor `claude mcp add --transport`.
  Source: <https://code.claude.com/docs/en/mcp.md>
- **Env var expansion syntax is `${VAR}` and `${VAR:-default}`. It works in command, args, env, url (HTTP types) and headers. An unset variable with no default leaves the literal `${VAR}` text in place and shows a warning in `claude mcp list`.** [high, load-bearing]
  The official example uses "url": "${API_BASE_URL:-https://api.example.com}/mcp" and "Authorization": "Bearer ${API_KEY}". `/mcp`, `claude mcp list` and `claude mcp get` show references by name, not by resolved value.
  Source: <https://code.claude.com/docs/en/mcp.md#environment-variable-expansion-in-mcp-json>
- **In a remote server's url and headers, Claude Code reads certain credential variables as empty: its own (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN), cloud provider credentials (e.g. AWS_BEARER_TOKEN_BEDROCK), and others like HTTPS_PROXY and NPM_TOKEN. Any `:-default` on those names is ignored.** [high, load-bearing]
  The docs list names with 'such as', so the list is not exhaustive. Their advice is to copy the credential into a variable with your own name. In practice, use names like GITHUB_MCP_PAT or LOGFIRE_MCP_TOKEN, not GITHUB_TOKEN or GH_TOKEN, because it is unverified whether those are blocked. Symptom: the server receives 'Bearer ' and returns 401. The debug log line contains 'never expanded toward a remote server'.
  Source: <https://code.claude.com/docs/en/mcp.md#credential-variables-that-read-as-empty>
- **Before using project-scoped servers in an interactive session, Claude Code asks for approval. You reset those choices with `claude mcp reset-project-choices`. In `claude -p`, Agent SDK and cloud sessions it loads project servers without asking.** [high, load-bearing]
  Until you approve, `claude mcp list` shows '⏸ Pending approval (run `claude` to approve)'. To keep a server out of non-interactive runs, use disabledMcpjsonServers, --setting-sources, or --strict-mcp-config. In an untrusted folder, approval keys committed in the project's .claude/settings.json are ignored. Approvals from user settings, managed settings and --settings still apply, and an untracked .claude/settings.local.json counts only once the folder is trusted.
  Source: <https://code.claude.com/docs/en/mcp.md#project-scope>
- **Approval settings keys: `enableAllProjectMcpServers` (boolean), `enabledMcpjsonServers` (array of .mcp.json server names) and `disabledMcpjsonServers` (array). The approval dialog writes them to .claude/settings.local.json, and a rejection wins over both kinds of approval.** [high, load-bearing]
  All three can go in any settings file. The documented example is {"enabledMcpjsonServers": ["memory", "github"]}. For enableAllProjectMcpServers, in a trusted folder a false in a higher-precedence file overrides a true in a lower one.
  Source: <https://code.claude.com/docs/en/settings-reference.md#enabledmcpjsonservers>
- **`claude mcp add` has three scopes. local is the default, private, and stored in ~/.claude.json under the project path. project is shared and written to .mcp.json at the repo root. user covers all your projects and is stored in ~/.claude.json. Precedence is local > project > user > plugin servers > claude.ai connectors, and whole entries win with no field merging.** [high, load-bearing]
  Duplicates across the three scopes are matched by name. Plugins and connectors are matched by endpoint, and a different path or query string counts as a different server. `claude mcp add-json <name> '<json>'` accepts --scope, and `claude mcp list`, `get` and `remove` manage servers. MCP 'local scope' (~/.claude.json) is not the same as .claude/settings.local.json.
  Source: <https://code.claude.com/docs/en/mcp.md#mcp-installation-scopes>
- **MCP permission rule names: `mcp__<server>` or `mcp__<server>__*` matches every tool on that server, and `mcp__<server>__<tool>` matches one tool. Allow-rule globs are only valid after a literal `mcp__<server>__` prefix. Deny rules may use `mcp__*`.** [high, load-bearing]
  An unanchored allow glob such as "mcp__*" is skipped with a warning. When settings load, any mcp__ rule with parentheses (parameter matching) is skipped; parameter matching only works with --disallowedTools. Tools from claude.ai connectors appear as mcp__claude_ai_<server>__<tool>.
  Source: <https://code.claude.com/docs/en/permissions.md>
- **Remote OAuth runs through `/mcp` in a session or `claude mcp login <name>` in the shell (`claude mcp logout <name>` clears it). `claude -p` and the SDK cannot run OAuth, so you must sign in interactively first. If you configured an Authorization header and the server rejects it, Claude Code does not fall back to OAuth.** [high]
  Tokens are stored and refreshed automatically. `claude mcp login --no-browser` prints a URL for headless setups. Pre-registered OAuth clients are supported through add-json's "oauth": {"clientId":..., "callbackPort":...} with --client-secret.
  Source: <https://code.claude.com/docs/en/mcp.md#authenticate-with-remote-mcp-servers>
- **CLAUDE.md locations, from broadest to most specific: managed policy (macOS: /Library/Application Support/ClaudeCode/CLAUDE.md), user ~/.claude/CLAUDE.md, project ./CLAUDE.md or ./.claude/CLAUDE.md, and local ./CLAUDE.local.md (gitignore it). Files in parent directories load at launch. CLAUDE.md files in subdirectories load the first time Claude reads or edits a file in that subdirectory.** [high, load-bearing]
  Files are concatenated, not overridden, and closer files are read last. The docs target under 200 lines per file, and files over 4 MiB are skipped. `/init` generates or improves a CLAUDE.md, and CLAUDE_CODE_NEW_INIT=1 switches to an interactive flow. `/memory` lists and opens memory files and toggles auto memory, which is stored at ~/.claude/projects/<project>/memory/. `/context` shows what loaded. Block-level HTML comments are stripped. AGENTS.md is read when no CLAUDE.md exists (v2.1.277+). The project-root CLAUDE.md is re-read after /compact.
  Source: <https://code.claude.com/docs/en/memory.md>
- **`@path/to/file` imports: relative paths resolve from the importing file, and imports can nest at most 4 hops. Imports inside code spans or fences are ignored. Imports that point outside the working directory trigger a one-time approval dialog. Imports do not reduce context cost because they load at launch.** [high]
  Spaces in paths are escaped with backslashes, and quoted paths are not imported. To share personal notes across worktrees, use `@~/.claude/my-project-instructions.md`, because a gitignored CLAUDE.local.md exists only in the worktree where you created it.
  Source: <https://code.claude.com/docs/en/memory.md#import-additional-files>
- **.claude/rules/: .md files are found recursively. A rule without `paths` frontmatter loads at launch with the same priority as .claude/CLAUDE.md. A rule with `paths:` (a YAML list or comma-separated globs) loads when Claude reads, writes or edits a matching file. `paths` is the only frontmatter field rules read.** [high, load-bearing]
  Brace expansion is supported, with a shared budget of 1,000 expanded patterns. If the YAML is invalid, the frontmatter is ignored and the rule loads for every file. User-level rules in ~/.claude/rules/ load before project rules. Symlinks are supported; links pointing outside the project need external-import approval. Path-scoped rules reload on demand after /compact.
  Source: <https://code.claude.com/docs/en/memory.md#path-specific-rules>
- **Worktrees: `claude --worktree <name>` (short form `-w`) creates `<repo>/.claude/worktrees/<name>/` on a new branch `worktree-<name>`, branched from the remote default branch by default. Running it again in a second terminal with a different name gives a parallel session. There is no `/worktree` slash command; mid-session, Claude uses the EnterWorktree/ExitWorktree tools when asked.** [high, load-bearing]
  The CLI reference lists `--worktree, -w` and `--tmux`, which requires --worktree (https://code.claude.com/docs/en/cli-reference.md). The commands reference has no /worktree entry (https://code.claude.com/docs/en/commands.md). If you omit the name, Claude generates one. `--worktree "#1234"` or a PR URL branches from that PR, creating .claude/worktrees/pr-<n>. Interactive use requires workspace trust. The docs advise adding .claude/worktrees/ to .gitignore. `worktree.baseRef` accepts "fresh" (default) or "head".
  Source: <https://code.claude.com/docs/en/worktrees.md>
- **`.worktreeinclude` at the project root uses .gitignore syntax. A file is copied into a new worktree only if it matches a pattern and is also gitignored, so tracked files are never duplicated.** [high, load-bearing]
  It applies to --worktree sessions, subagent worktrees and desktop-app parallel sessions. A worktree is a fresh checkout, so you still install dependencies (e.g. the uv venv) in each one.
  Source: <https://code.claude.com/docs/en/worktrees.md#copy-gitignored-files-into-worktrees>
- **Worktree cleanup: on exit, a clean unnamed worktree and its branch are removed automatically. A named session, or a worktree that holds work, triggers a keep/remove prompt. `-p` runs never clean up; use `git worktree remove` (after `git worktree unlock` if it is locked).** [high]
  A worktree you keep can be resumed with `claude --worktree <name> --resume`. Subagent and background-session worktrees are swept after cleanupPeriodDays. Worktrees share the .git directory, project-scope plugins and 'don't ask again' approvals (saved to the main checkout's .claude/settings.local.json).
  Source: <https://code.claude.com/docs/en/worktrees.md#clean-up-worktrees>
- **Checkpointing: each prompt that starts a turn creates a checkpoint. `/rewind` (aliases /checkpoint and /undo), or Esc twice on an empty prompt, opens a menu: Restore code and conversation, Restore conversation, Restore code, Summarize from here, Summarize up to here, Never mind.** [high]
  Snapshots are kept for the 100 most recent checkpoints and persist across resume, but are deleted after roughly 30 days by the retention sweep. Limits: changes made through Bash (rm/mv/cp) are not tracked, most subagent edits and background /code-review --fix edits are not restored, external edits are not tracked, and symlinked or hard-linked files are skipped. It is not a replacement for git.
  Source: <https://code.claude.com/docs/en/checkpointing.md>
- **Claude Code GitHub Action: `anthropics/claude-code-action@v1`. The docs examples use @v1, and the latest tagged release is v1.0.249, published 2026-10-14. Quick setup is `/install-github-app`, which requires repo admin, the gh CLI authenticated, and a github.com remote. Manual setup means copying examples/claude.yml from the action repo.** [high, load-bearing]
  Release tags come from `gh api repos/anthropics/claude-code-action/releases` (v1.0.249 at 2026-10-14T02:57:56Z; the floating 'v1' release dates from 2025-08-26). Upgrading from beta: change @beta to @v1, remove `mode`, rename direct_prompt to prompt, and move max_turns and model into claude_args. Inputs: prompt, claude_args, anthropic_api_key, claude_code_oauth_token, github_token, plugin_marketplaces, plugins, settings, trigger_phrase, use_bedrock, use_vertex, use_foundry.
  Source: <https://code.claude.com/docs/en/github-actions.md>
- **Action secrets are either `ANTHROPIC_API_KEY` (a Claude Console API key, passed as `anthropic_api_key:`) or `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`, for Pro, Max, Team or Enterprise subscriptions, passed as `claude_code_oauth_token:`).** [high, load-bearing]
  An OAuth token is tied to the subscription of whoever generated it, so the docs recommend an API key for org-shared secrets. Interactive mode applies when there is no prompt input (it responds to @claude). Automation mode applies when a prompt is set. Triggering users need write access, bots are rejected unless listed in allowed_bots, and fork PRs do not get secrets. Commits made with the default GITHUB_TOKEN do not trigger CI, so omit github_token to act as the Claude GitHub App.
  Source: <https://code.claude.com/docs/en/github-actions.md#manual-setup>
- **Review commands: `/code-review [low|medium|high|xhigh|max|ultra] [--fix] [--comment] [--max-findings ...] [pr#|branch|path]` is a bundled skill that reviews the current diff for correctness bugs, running as a background subagent. `/review` has been an alias of it since v2.1.223. `/security-review` checks the current branch's diff against origin's default branch for vulnerabilities and needs an `origin` remote. `/code-review ultra` (alias /ultrareview) runs a multi-agent review in the cloud.** [high, load-bearing]
  Ultrareview includes 3 free runs on Pro and Max, then needs usage credits. `/simplify` is for cleanups only. The local /code-review follows CLAUDE.md but not REVIEW.md. The managed 'Code Review' GitHub service is a research preview for Team and Enterprise only, averaging $15-25 per review (https://code.claude.com/docs/en/code-review.md), so it is not available to a solo Pro/Max learner. Earlier versions had different /review behavior, so lessons should state the version they describe.
  Source: <https://code.claude.com/docs/en/commands.md>
- **GitHub MCP (remote): URL https://api.githubcopilot.com/mcp/ with header `Authorization: Bearer <PAT>` (a fine-grained PAT, per Claude Code's own example). For read-only access, append `/readonly` to the URL (e.g. https://api.githubcopilot.com/mcp/readonly) or send the header `X-MCP-Readonly: true`. `X-MCP-Toolsets` (e.g. "repos,issues") limits which toolsets are exposed.** [high, load-bearing]
  Claude Code's docs show `claude mcp add --transport http github https://api.githubcopilot.com/mcp/ --header "Authorization: Bearer YOUR_GITHUB_PAT"` (https://code.claude.com/docs/en/mcp.md#example-connect-to-github-for-code-reviews). GitHub's guide uses add-json with the URL without a trailing slash (https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-claude.md). Remote OAuth needs a registered GitHub App or OAuth app, with no dynamic client registration. This session's own GitHub connector failed with 'does not support dynamic client registration', so use a PAT through an env var (medium confidence that OAuth will not work out of the box). Probe: /mcp/readonly returns 401 without auth, so the endpoint exists.
  Source: <https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md>
- **Neon MCP: hosted Streamable HTTP server at https://mcp.neon.tech/mcp. For OAuth in Claude Code run `npx add-mcp https://mcp.neon.tech/mcp -a claude-code`; for an API key run `claude mcp add --transport http neon https://mcp.neon.tech/mcp --header "Authorization: Bearer <YOUR_NEON_API_KEY>"`. URL parameters `?readonly=true`, `?projectId=<id>` and `?category=<name>` (repeatable) restrict what it can do.** [high, load-bearing]
  From https://neon.com/docs/ai/neon-mcp-server: with OAuth you can choose read-only scope during the consent step. The /sse endpoint is deprecated and stops working on or after 2026-10-01 (returning 410). The local stdio package @neondatabase/mcp-server-neon is deprecated. Neon recommends MCP for development and testing only, never production DBs or PII. `npx neon@latest init` or `npx neon@latest plugins` installs the Neon plugin with skills.
  Source: <https://neon.com/docs/ai/connect-mcp-clients-to-neon>
- **Vercel MCP is OAuth-only at https://mcp.vercel.com: `claude mcp add --transport http vercel https://mcp.vercel.com`, then authenticate with /mcp. Logfire uses OAuth at https://logfire-us.pydantic.dev/mcp (EU: https://logfire-eu.pydantic.dev/mcp) through `claude mcp login logfire`, or an API key with project:read scope via `${LOGFIRE_MCP_TOKEN}`. Context7 is at https://mcp.context7.com/mcp with `Authorization: Bearer <API key>`, or https://mcp.context7.com/mcp/oauth for OAuth.** [high, load-bearing]
  Vercel: connecting gives the AI the same access as your Vercel user, and no read-only mode is documented. Logfire (https://logfire.pydantic.dev/docs/how-to-guides/mcp-server/): the docs give an exact Claude Code .mcp.json for key auth, offer the alternative `claude plugin install logfire@claude-plugins-official` plus `claude mcp login plugin:logfire:logfire`, and note a daily query budget per org on Logfire Cloud. Context7 (https://context7.com/docs/resources/all-clients and https://github.com/upstash/context7): `claude mcp add --scope user --header "Authorization: Bearer YOUR_API_KEY" --transport http context7 https://mcp.context7.com/mcp`. OAuth works only on the remote HTTP endpoint, and a free API key gives higher rate limits.
  Source: <https://vercel.com/docs/agent-resources/vercel-mcp>

### Exact snippets (copied from the sources named)

**Claude Code official .mcp.json env-var expansion example** — <https://code.claude.com/docs/en/mcp.md#example-with-variable-expansion>

```json
{
  "mcpServers": {
    "api-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

**COMPOSED (not verbatim): suggested project .mcp.json for this stack, assembled from the documented URLs/headers. Entries with no headers use OAuth through /mcp; GITHUB_MCP_PAT is a custom name chosen to avoid the blocked credential names** — <https://code.claude.com/docs/en/mcp.md#project-scope>

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_MCP_PAT}",
        "X-MCP-Toolsets": "repos,issues,pull_requests,actions",
        "X-MCP-Readonly": "true"
      }
    },
    "neon": {
      "type": "http",
      "url": "https://mcp.neon.tech/mcp?readonly=true"
    },
    "vercel": {
      "type": "http",
      "url": "https://mcp.vercel.com"
    },
    "logfire": {
      "type": "http",
      "url": "https://logfire-us.pydantic.dev/mcp"
    },
    "context7": {
      "type": "http",
      "url": "https://mcp.context7.com/mcp/oauth"
    }
  }
}
```

**GitHub remote MCP: official headers example (toolsets + read-only)** — <https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md>

```json
{
    "type": "http",
    "url": "https://api.githubcopilot.com/mcp/",
    "headers": {
        "X-MCP-Toolsets": "repos,issues",
        "X-MCP-Readonly": "true",
        "X-MCP-Lockdown": "false"
    }
}
```

**Pydantic Logfire MCP: official Claude Code .mcp.json with API key via env var** — <https://logfire.pydantic.dev/docs/how-to-guides/mcp-server/>

```json
{
  "mcpServers": {
    "logfire": {
      "type": "http",
      "url": "https://logfire-us.pydantic.dev/mcp",
      "headers": {
        "Authorization": "Bearer ${LOGFIRE_MCP_TOKEN}"
      }
    }
  }
}
```

**Path-scoped rule file (.claude/rules/<topic>.md) frontmatter** — <https://code.claude.com/docs/en/memory.md#path-specific-rules>

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API Development Rules

- All API endpoints must include input validation
- Use the standard error response format
- Include OpenAPI documentation comments
```

**.worktreeinclude (copies gitignored env files into new worktrees)** — <https://code.claude.com/docs/en/worktrees.md#copy-gitignored-files-into-worktrees>

```text
.env
.env.local
config/secrets.json
```

**Official PR code-review workflow using claude-code-action@v1 (replace the anthropic_api_key line with claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }} for subscription auth)** — <https://code.claude.com/docs/en/github-actions.md#run-a-skill>

```yaml
name: Code Review
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      issues: read
      id-token: write
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 1
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          plugin_marketplaces: "https://github.com/anthropics/claude-code.git"
          plugins: "code-review@claude-code-plugins"
          prompt: "/code-review:code-review --comment ${{ github.repository }}/pull/${{ github.event.pull_request.number }}"
          claude_args: '--allowedTools "mcp__github_inline_comment__create_inline_comment"'
```

**Pre-approve specific .mcp.json servers in settings (put in ~/.claude/settings.json or .claude/settings.local.json; ignored in a committed project settings file until the folder is trusted)** — <https://code.claude.com/docs/en/settings-reference.md#enabledmcpjsonservers>

```json
{
  "enabledMcpjsonServers": ["memory", "github"]
}
```

### Recommendations
- Commit a .mcp.json that holds no secrets. OAuth servers (Neon, Vercel, Logfire, Context7 /mcp/oauth) get bare URLs; token servers use ${VAR} references with names you choose yourself (e.g. GITHUB_MCP_PAT, LOGFIRE_MCP_TOKEN), never ANTHROPIC_* or other names that may be read as empty. Keep the real values in a gitignored .env exported in your shell.
- Start every MCP server in least-privilege mode: GitHub with X-MCP-Readonly: true (or the /readonly URL) and a narrow X-MCP-Toolsets list; Neon with ?readonly=true&projectId=<dev project> on a dev branch only. Add `deny` rules such as mcp__vercel__* for write-capable tools you don't need yet. Vercel has no documented read-only mode.
- Teach and use memory in layers: run /init, then trim CLAUDE.md to under 200 lines. Put backend- and agent-specific conventions in path-scoped .claude/rules/ (e.g. paths: "app/agents/**/*.py", "app/api/**/*.py"), put personal notes in a gitignored CLAUDE.local.md, and check what loaded with /context.
- For parallel work, run `claude -w <name>` in two terminals at most (the Mac has limited RAM, and each worktree needs its own venv/node_modules). Add .claude/worktrees/ to .gitignore and add .env to .worktreeinclude. Teach `git worktree list` and `git worktree remove` for cleanup.
- For CI, use anthropics/claude-code-action@v1 through /install-github-app. A solo Pro/Max learner can use a CLAUDE_CODE_OAUTH_TOKEN secret from `claude setup-token`; for reproducible builds, consider pinning to v1.0.249 or a commit SHA. Use the documented code-review workflow. Skip the managed Code Review service (Team/Enterprise only) and use /code-review and /security-review locally.
- Track 3's RAG docs re-sync can use https://code.claude.com/docs/llms.txt as the page index, and each page is available as raw Markdown by appending .md. Claude Code also documents a hosted docs MCP server at https://code.claude.com/docs/mcp (it answered initialize with HTTP 200). Version-stamp each lesson, because many behaviors are gated on Claude Code v2.1.2xx releases.
- Teach /rewind as session-level undo, and spell out its limits: it does not track Bash file changes or background subagent and /code-review --fix edits. Pair it with frequent git commits on feature branches.
- In the GitHub track, explain that project .mcp.json servers load without an approval prompt in `claude -p`, the SDK and CI. A committed .mcp.json therefore becomes part of CI's attack surface; keep CI on --strict-mcp-config or use disabledMcpjsonServers where appropriate.

### Risks
- The docs change very fast. Many statements carry version gates (v2.1.198 through v2.1.296), and /review changed meaning at v2.1.223. Lesson text and quiz answers that hardcode behavior will go stale, so the scheduled re-sync and the rubric for open questions need to account for that.
- The list of credential names that read as empty is not exhaustive ('such as'). Using GITHUB_TOKEN or GH_TOKEN in a header could silently send 'Bearer ' and fail with 401.
- Duplicate servers: plugins and connectors are deduplicated by endpoint, and a different query string counts as a different server. A Neon plugin at mcp.neon.tech/mcp plus a .mcp.json entry at mcp.neon.tech/mcp?readonly=true would both connect, exposing duplicate tools and the plugin's write tools. This session's environment already shows a Neon plugin and a Vercel connector.
- Neon and Vercel MCP grant broad account access. Neon explicitly says dev/test only, and Vercel gives the agent the same access as the user, with prompt-injection exposure, so a beginner's agent could change production resources.
- The GitHub remote MCP OAuth flow probably won't work in Claude Code without a pre-registered OAuth app (no dynamic client registration), so learners will need a fine-grained PAT, which has to be stored and rotated safely.
- A CLAUDE_CODE_OAUTH_TOKEN in Actions is tied to one person's subscription. Spending and terms depend on the plan; an API key with spend limits may be safer.
- anthropics/claude-code-security-review is used at @main with no release tags (last push 2026-02-11). If referenced in lessons, it is less stable than claude-code-action.
- Worktrees on a low-RAM Mac: each worktree needs its own dependencies, running two dev servers plus two Claude sessions may cause swapping, and a forgotten worktree from a -p run is never cleaned up automatically.

### Open questions
- Exactly which environment variable names are in Claude Code's 'read as empty' set for remote url/headers? (In particular GITHUB_TOKEN, GH_TOKEN, NEON_API_KEY.) The docs give only examples.
- Can Claude Code complete OAuth against the GitHub remote MCP server using pre-configured client credentials (add-json "oauth": {clientId, callbackPort} plus --client-secret) with a user-registered GitHub OAuth app? Not tested.
- Which Claude Code version is installed on the learner's Mac? Several features cited (AGENTS.md reading, .worktreeinclude ** semantics, the /review alias, automatic SSE fallback) need a specific v2.1.2xx or later.
- Does Vercel MCP offer project-scoped URLs or a read-only option? The current Vercel docs page does not mention either.
- Is using a personal CLAUDE_CODE_OAUTH_TOKEN in a public repo's GitHub Actions acceptable under the learner's plan terms, and how does it count against subscription usage limits?
- Should the tutor's RAG for track 3 ingest the .md pages from llms.txt directly, or query the hosted docs MCP (https://code.claude.com/docs/mcp)? Its tool surface and terms of use were not inspected.

### Fact-check (second agent re-read the sources)

I compared every claim with the current source text on 2026-10-14. I pulled the code.claude.com .md pages and the github-mcp-server raw markdown with curl, and checked release data with the GitHub releases API. All 17 claims hold. None needs a factual correction.

Small points the claims leave out, and where the snippets came from:
1. Claim 4: Claude Code also skips the project-server approval prompt in a bypassPermissions session when skipDangerousModePermissionPrompt is set in user or managed settings.
2. Claim 9: a symlinked rule whose target is outside the working directory needs external-import approval. Even after approval, only linked rules without `paths` load. The brace budget is 1,000 expanded patterns and also 4 MiB.
3. Claim 10: with the default `fresh` base, Claude Code falls back to the local HEAD when there is no remote and origin/HEAD is not cached locally. `claude -p --worktree` skips the trust check.
4. Claim 12: the API returned v1.0.249 published 2026-10-14T02:57:56Z. The floating v1 release's published_at is 2025-08-26 and its created_at is 2026-10-14 (the tag was moved).
5. Claim 15: GitHub's Claude install guide states the remote-OAuth limitation only for Claude Desktop custom connectors. A probe of /mcp/readonly without auth returned 401, which confirms the endpoint exists.
6. Claim 16: Neon's /sse endpoint shut-off date (on or after 2026-10-01) has already passed as of today.
7. Snippets 1 and 3 to 7 match the official examples word for word, including the .worktreeinclude example in worktrees.md and the YAML in github-actions.md#run-a-skill.

Snippet checks:
- Snippet 1 (official env-var expansion example): none, matches mcp.md exactly.
- Snippet 2 (COMPOSED .mcp.json): no key, nesting or value errors. type http, url and headers are valid; the toolset names repos, issues, pull_requests and actions are valid; X-MCP-Readonly "true" is valid. Caveat: Claude Code matches plugin servers to project servers by endpoint, and a different query string counts as a different server. If the Neon plugin is also enabled (it is installed in this environment), https://mcp.neon.tech/mcp?readonly=true does not de-duplicate against the plugin's server, so both connect and the plugin's write tools stay exposed. The same applies to a Logfire or Vercel plugin if their URLs differ.
- Snippet 2 caveat: Vercel documents only OAuth, and only for reviewed clients. Claude Code is on that list, so the no-header entry is correct.
- Snippet 3 (GitHub headers example): none, matches remote-server.md exactly.
- Snippet 4 (Logfire .mcp.json): none, matches exactly. The cited URL now 301-redirects to https://pydantic.dev/docs/logfire/guides/mcp-server/.
- Snippet 5 (path-scoped rule frontmatter): none, matches memory.md exactly.
- Snippet 6 (.worktreeinclude): none, matches the worktrees.md example exactly.
- Snippet 7 (code-review workflow YAML): none, matches github-actions.md#run-a-skill exactly, including actions/checkout@v6, the permissions block, plugin_marketplaces, plugins, prompt and claude_args.
- Snippet 8 (enabledMcpjsonServers): the JSON is fine. The snippet's caption needs one fix: an untracked .claude/settings.local.json is also applied only after the folder is trusted. The exception is a folder that is the user's config home (home directory or CLAUDE_CONFIG_DIR). Only ~/.claude/settings.json, managed settings and --settings apply in an untrusted folder.

## Claude Code v2.1.299 harness specifics for an autonomous, worktree-based build of a public FastAPI/Pydantic AI learning site: plugins, subagent model routing, permissions, worktrees, /goal and /loop, hooks, output styles

**Summary.** A project's committed .claude/settings.json can declare plugins with `enabledPlugins` and marketplaces with `extraKnownMarketplaces`, but repository marketplaces only register after the user accepts the workspace trust dialog. Only plugins whose marketplace entry is a relative path load on their own. In the official marketplace those are hookify, frontend-design and github. firecrawl, tavily, vercel, logfire, pydantic-ai and neon use external sources, so each machine must run `claude plugin install <name>@claude-plugins-official --scope project`. Claude Code does not prompt you to install them; it shows an "enabled in project settings but isn't installed here" entry in the /plugin Errors tab. Octen ships its own Claude Code marketplace and plugin (`claude plugin marketplace add Octen-Team/octen-mcp`, then `claude plugin install octen@octen`). Its plugin source is "./", so it loads automatically once the marketplace is registered. Subagent `model` accepts sonnet, opus, haiku, fable, inherit, or a full ID (claude-fable-5-1, claude-opus-5-5, claude-sonnet-5-5 and claude-haiku-5-5 are confirmed). Since v2.1.251, CLAUDE_CODE_SUBAGENT_MODEL is only a default: frontmatter and per-call models beat it unless CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1 is also set. `/tasks` shows each subagent's real model and effort. Auto mode is already the built-in starting mode for interactive terminal sessions on v2.1.283 and later. It cannot be set from project or local settings, and it pauses back into prompts after 3 blocks in a row or 20 in total. Its default classifier rules block "merging a pull request no human has approved", which conflicts directly with the planned auto-merge flow. /goal and /loop are both session-scoped: /loop needs the session open and idle and expires after 7 days. The Learning output style deliberately stops at TODO(human) and would stall unattended runs.

### Findings

- **A project's .claude/settings.json can declare plugins: `enabledPlugins` maps "plugin@marketplace" to true/false, and `extraKnownMarketplaces` maps a marketplace name to {source:{...}, autoUpdate?}.** [high]
  Both keys have scope 'Any file'. Source types are github{repo}, git{url}, url{url, headers?, headersHelper?}, file{path}, directory{path} and settings{name, plugins}. `additionalMarketplaces` is an alias on v2.1.232 and later. Precedence for each plugin id is managed > --settings flag > local > project > user. To opt out of a project-enabled plugin, a user sets it to false in .claude/settings.local.json.
  Source: <https://code.claude.com/docs/en/settings-reference.md>
- **On a fresh clone, repository `extraKnownMarketplaces` apply only after the workspace trust dialog is accepted, and only relative-path plugins load without an install step. External-source plugins are not fetched and there is no install prompt.** [high]
  In an untrusted folder, including a `-p` run, the entries are ignored with no message. Once trusted, Claude Code clones the declared marketplace in the background and reloads plugins. A plugin enabled only in project settings whose entry points to an external source (GitHub, url, git-subdir, npm) shows `Plugin "<name>" is enabled in project settings but isn't installed here` in the /plugin Errors tab. The guidance is to run `claude plugin install <name>@<marketplace> --scope project` and then /reload-plugins. MCP servers from a repo-supplied plugin go through the same per-server approval as .mcp.json, and background monitors don't load. In -p/CI runs, plugins install in the background unless CLAUDE_CODE_SYNC_PLUGIN_INSTALL=1. Plugins installed at project scope from the main checkout also load in its worktrees (v2.1.200+).
  Source: <https://code.claude.com/docs/en/plugins/org.md>
- **All nine requested plugins exist in anthropics/claude-plugins-official (marketplace name `claude-plugins-official`, 315 plugins). hookify, frontend-design and github use relative paths. firecrawl, tavily, vercel, logfire, pydantic-ai and neon use external sources.** [high]
  Read with `gh api .../.claude-plugin/marketplace.json`. Sources: hookify ./plugins/hookify; frontend-design ./plugins/frontend-design; github ./external_plugins/github; firecrawl url firecrawl/firecrawl-claude-plugin.git; tavily url tavily-ai/skills.git; vercel url vercel/vercel-plugin.git; logfire git-subdir pydantic/skills plugins/logfire; pydantic-ai git-subdir pydantic/skills plugins/ai; neon git-subdir neondatabase/agent-skills plugins/neon-postgres. The github plugin's .mcp.json points at https://api.githubcopilot.com/mcp/ with `Authorization: Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}`, so it needs a PAT env var; gh CLI login alone does not supply that token. The official marketplace is added automatically the first time you start an interactive terminal session.
  Source: <https://github.com/anthropics/claude-plugins-official/blob/main/.claude-plugin/marketplace.json>
- **Shell commands: `claude plugin marketplace add <source> [--scope user|project|local]` and `claude plugin install <plugin>@<marketplace> [-s user|project|local]` (default scope user). `--marketplace <source>` installs and adds the marketplace in one step (v2.1.292+).** [high]
  On a machine where no interactive session has run yet, a script must run `claude plugin marketplace add anthropics/claude-plugins-official` before installing from it. `claude plugin install ... --marketplace` declares the marketplace in user settings even when you pass --scope project. Use `claude plugin list` (shows Scope/Status) to verify.
  Source: <https://code.claude.com/docs/en/plugins/install.md>
- **Octen ships a Claude Code plugin marketplace in Octen-Team/octen-mcp: marketplace name `octen`, plugin `octen`, source "./" (relative), version 0.6.0. It provides a hosted MCP server and two skills.** [high]
  README install: `claude plugin marketplace add Octen-Team/octen-mcp` then `claude plugin install octen@octen`. The plugin carries no credential: the first call returns 401 and Claude Code walks you through OAuth (or start it with /mcp). Alternatives: `claude mcp add --transport http octen https://mcp.octen.ai/mcp --header "x-api-key: ..."` or the local `npx -y octen-mcp` with OCTEN_API_KEY. Octen is not in the official marketplace. Because the source is relative, declaring it in project extraKnownMarketplaces plus enabledPlugins should load it after trust with no separate install.
  Source: <https://github.com/Octen-Team/octen-mcp>
- **Subagent `model` frontmatter accepts sonnet, opus, haiku, fable, a full model ID, or inherit. `fable` is an alias that resolves to Fable 5.1 (claude-fable-5-1).** [high]
  On the Anthropic API, opus resolves to Opus 5.5 (claude-opus-5-5), sonnet to Sonnet 5.5 and haiku to Haiku 5.5. The platform model list confirms claude-sonnet-5-5, claude-haiku-5-5, claude-opus-5-5 and claude-fable-5-1. Sonnet 5.5 needs v2.1.284+, Opus 5.5 v2.1.280+, Haiku 5.5 v2.1.293+, Fable 5.1 v2.1.257+. A family alias in frontmatter resolves to the main conversation's exact model when the main session is in the same family.
  Source: <https://code.claude.com/docs/en/model-config.md>
- **Subagent model order is: per-invocation model, then frontmatter `model` (inherit means the main model), then CLAUDE_CODE_SUBAGENT_MODEL, then the main conversation's model. The environment variable does NOT override frontmatter unless CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1.** [high]
  Before v2.1.251 the env var came first. With FORCE=1 (v2.1.257+), frontmatter `model` is ignored and Claude can't pass a model. Setting only the env var also doesn't change the built-in Explore and Plan agents. A mod's agent.spawn hook can replace the per-invocation model.
  Source: <https://code.claude.com/docs/en/sub-agents.md>
- **Subagent `effort` accepts low, medium, high, xhigh or max. It overrides the session effort but not CLAUDE_CODE_EFFORT_LEVEL; a per-invocation effort (v2.1.292+) overrides the field.** [high]
  Fable 5.1/5 and Opus/Sonnet/Haiku 5.5 support all five levels. Opus 5.5, Sonnet 5.5 and Haiku 5.5 default to medium; most others default to high. An unsupported level falls back to the highest supported level at or below it. Setting CLAUDE_CODE_EFFORT_LEVEL globally flattens per-agent effort.
  Source: <https://code.claude.com/docs/en/model-config.md>
- **If a requested model is unavailable, the substitution is not silent in interactive sessions, and there is no cross-model failover unless you configure `fallbackModel`.** [high]
  If a subagent's model is blocked by availableModels or the org, Claude Code substitutes the newest permitted version of the family or the inherited model, and shows a warning naming both in interactive sessions. If a model is overloaded or unavailable, it switches only if a `fallbackModel` chain (max 3) or `--fallback-model` is set; otherwise it retries and then surfaces the error. Subagents continue on the fallback (v2.1.247+). Separately, Fable, Opus 5.5 and Sonnet 5.5 requests flagged by safety classifiers (cyber/bio) re-run on Opus 4.8, Opus 5 or Sonnet 5. In subagents this happens without a prompt, and the main session stays on the fallback afterwards. /goal is cleared if a turn fails with 'a model that isn't available'.
  Source: <https://code.claude.com/docs/en/model-config.md>
- **Fable may bill to usage credits. Its mid-session consent prompt is held in background sessions for `dialogExpiry` (default 5m), after which the turn ends without sending the request, which stalls unattended Fable runs.** [medium]
  Depending on plan and seat tier, Fable bills to usage credits. Once you choose to continue on credits, the prompt doesn't reappear. In -p runs Claude Code bills without asking. Neither Fable model is a default on any plan; you select it with /model fable or --model fable.
  Source: <https://code.claude.com/docs/en/model-config.md>
- **To see each agent's real model: `/tasks` names the model and effort on each subagent row (v2.1.242+). Main session: /status or a status line. Background sessions: the agent view header shows the dispatch model. Workflows: /workflows.** [high]
  Subagent transcripts are stored at ~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl, kept 30 days by default. The docs suggest running /tasks while a subagent is running to confirm CLAUDE_CODE_SUBAGENT_MODEL(_FORCE) took effect. The docs do not state whether /workflows shows a per-agent model.
  Source: <https://code.claude.com/docs/en/sub-agents.md>
- **The main session model and effort for a project can be set in .claude/settings.json with `model` (alias or ID) and `effortLevel` (low|medium|high|xhigh; max is not accepted). In project files, `effortLevel` applies to every model, including Opus 5.5.** [high]
  Model priority: /model, then --model, then ANTHROPIC_MODEL, then settings `model`, then ANTHROPIC_DEFAULT_MODEL. /model saves to user settings. A user-file top-level effortLevel is ignored by Opus 5.5 (per-model levels live in `modelSettings`, e.g. {"claude-opus-5-5":{"effortLevel":"high"}}). `max` can only come from CLAUDE_CODE_EFFORT_LEVEL or a session-only pick.
  Source: <https://code.claude.com/docs/en/settings-reference.md>
- **permissions.defaultMode accepts default (alias manual), acceptEdits, plan, auto, dontAsk or bypassPermissions. `auto` and `bypassPermissions` do not take effect from project or local settings; put them in ~/.claude/settings.json or pass --permission-mode.** [high]
  In v2.1.283 and later, the built-in starting mode for interactive terminal and VS Code sessions is auto. `claude -p` and the SDK start in `default` when feature flags are fetched, so unattended -p runs need --permission-mode auto. 'auto' in a project file falls through to the built-in default, while bypassPermissions there starts Manual. Another project value such as acceptEdits WOULD override the built-in auto, so don't set defaultMode in the committed file.
  Source: <https://code.claude.com/docs/en/permission-modes.md>
- **Auto mode can still stall: after 3 consecutive or 20 total classifier blocks it pauses and resumes prompting. Ask rules that match command content still prompt, and protected-path writes go to the classifier and are never approved by allow rules.** [high]
  Requirements: all plans; Anthropic API models Opus 4.6+, Sonnet 4.6+, Haiku 5.5 or Fable. The thresholds are not configurable. In -p without --permission-prompt-tool, the blocked action is skipped and the run continues. Protected paths include .git, .claude (except .claude/worktrees and agent-memory .md files), .vscode, .husky, .devcontainer, .pre-commit-config.yaml, .mcp.json and .claude.json, so an agent writing .claude/agents, .claude/hooks or hookify rules gets classifier review. AskUserQuestion is never auto-approved; the user-scope `askUserQuestionTimeout` lets it auto-continue.
  Source: <https://code.claude.com/docs/en/permission-modes.md>
- **The auto-mode classifier blocks by default 'Merging a pull request no human has approved, approving Claude's own pull request, or disabling CI checks'. It also blocks force push, `git reset --hard`, and sensitive details in PR/commit text on public repos.** [medium]
  This directly affects the plan to auto-merge PRs after an agent review. Custom `autoMode.allow` entries (user or managed scope only, not project) can override soft_deny rules, and explicit user intent naming the exact action can clear soft blocks, but hard_deny cannot be overridden. The docs page does not say whether the PR-merge rule is soft or hard; `claude auto-mode defaults` prints the rules. For public repos, internal file paths, code names and live API data in PR bodies count as sensitive details. Installing dependencies declared in lock files is allowed by default.
  Source: <https://code.claude.com/docs/en/permission-modes.md>
- **Allow-rule syntax is Bash(<prefix> *). Put the * after the subcommand, and every subcommand of a compound command must match on its own. Environment runners pass through, so a rule like `Bash(uv run *)` effectively allows any command.** [high]
  `Bash(ls *)` also matches bare `ls`, and `:*` is equivalent to a trailing ` *`. The docs name npx, devbox run, mise exec, direnv exec and docker exec as runners whose prefix rules match anything after them; `uv run` is the same pattern by analogy (not named in the docs), so allow `Bash(uv run pytest *)` and `Bash(uv run ruff *)` instead. Project allow rules apply only after workspace trust; deny and ask rules always apply. Auto mode suspends interpreter-style allow rules such as Bash(python *).
  Source: <https://code.claude.com/docs/en/permissions.md>
- **Rules are evaluated deny, then ask, then allow. A PreToolUse hook returning "allow" never bypasses a matching deny or ask rule, and a hook exiting with code 2 blocks the call before allow rules are evaluated.** [high]
  A deny anywhere (user, project, local or managed) beats allow everywhere. Bash deny rules match the command text as written, so `Bash(curl *)` doesn't stop /usr/bin/curl or `sh -c 'curl …'`; use the sandbox for hard boundaries. Mods' tool.check can override rules in some setups.
  Source: <https://code.claude.com/docs/en/permissions.md>
- **Background subagents surface each permission prompt in the main session, naming the subagent. Esc denies just that call, and an answer that lasts beyond one call applies to the whole session.** [high]
  Fork mode is on by default in interactive sessions, so subagents run in the background there. Background subagents get a reduced built-in toolset. In auto, acceptEdits or bypass main modes, the subagent's own `permissionMode` is ignored and it inherits the main mode. Plugin subagents ignore the hooks, mcpServers and permissionMode fields.
  Source: <https://code.claude.com/docs/en/sub-agents.md>
- **`claude -w <name>` (alias --worktree) creates .claude/worktrees/<name>/ on branch worktree-<name>. `isolation: worktree` in subagent frontmatter gives the subagent a temporary worktree branched from origin's default branch, unless worktree.baseRef is "head".** [high]
  Interactive -w requires prior workspace trust. Subagent worktrees with no changes are removed automatically; ones with changes stay until a sweep can remove them without losing work, and are git-worktree-locked while the agent runs. `.worktreeinclude` at the repo root (gitignore syntax) copies only files that match AND are gitignored. Approvals granted in a worktree save to the main checkout's settings.local.json. `worktree.location` is read only by the Desktop app for SSH sessions; CLI, subagents and background sessions always use .claude/worktrees/. Add .claude/worktrees/ to .gitignore.
  Source: <https://code.claude.com/docs/en/worktrees.md>
- **CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS (default 20, v2.1.217+) caps running subagents per session. CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS (1-256, default 16 or fewer on low-CPU machines, v2.1.269+) caps workflow agents. Both can go in the settings `env` block.** [medium]
  Both take plain digits; other values are ignored. Neither appears on the list of env vars that project or local settings can't set, and 'timeouts and limits' variables apply at startup from every settings file. Sessions with ultracode on are exempt from the subagent cap. CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY (default 10) also limits parallel read-only tools and subagents. Each workflow agent's transcript stays in memory.
  Source: <https://code.claude.com/docs/en/env-vars.md>
- **`/goal <condition>` (up to 4000 chars) starts a turn right away, and after each turn a small fast model judges met, not yet met or impossible from the transcript alone. It does not change the permission mode, so run it in auto mode.** [high]
  The goal clears on an auth failure, exhausted credits, a context overflow compaction can't clear, or an unavailable model. It pauses on rate or usage limits and retries transient errors up to 3 times. The loop stops after several turns with no tool use. Evaluation is skipped while subagents or background shells run, with check-ins at 30 minutes, then 1 hour, then every 2 hours (CLAUDE_CODE_GOAL_CHECKIN_MINUTES). The goal is restored on resume. `/goal clear` (or stop/off/reset/none/cancel) removes it. It requires workspace trust and is unavailable when disableAllHooks is set. It works in -p (`claude -p "/goal ..."`; add --output-format stream-json --verbose).
  Source: <https://code.claude.com/docs/en/goal.md>
- **`/loop [interval] [prompt]` takes intervals in s, m, h or d; without an interval Claude picks 1m to 1h each time. Tasks fire only while the session is open and idle, recurring tasks expire after 7 days, and a self-paced loop isn't restored on resume.** [high]
  Fixed intervals become cron jobs. Odd intervals are rounded, and seconds are rounded up to whole minutes. Prompts fire between turns, so a long /goal turn delays them, and missed fires don't catch up. Backgrounding the session carries /loop tasks over to a background session. CLAUDE_CODE_DISABLE_CRON=1 disables the scheduler. For durable scheduling use Routines, Desktop scheduled tasks or GitHub Actions.
  Source: <https://code.claude.com/docs/en/scheduled-tasks.md>
- **Command hooks run in exec form when `args` is present: `command` is spawned directly with no shell. PostToolUse uses matcher "Edit|Write", and exit code 2 there shows stderr to Claude.** [high]
  Handlers run in the current directory. When a session enters a worktree, ${CLAUDE_PROJECT_DIR} stays at the main checkout, while the input JSON `cwd` (and the hook's current directory) follows the worktree. The optional `if` field takes one permission rule (e.g. "Edit(**/*.py)"; Edit rules cover all file-editing tools in the permission system). Default timeout is 600s; `onFailure: block` needs v2.1.295+. Hooks in project settings run in -p without folder trust.
  Source: <https://code.claude.com/docs/en/hooks.md>
- **A plugin's hooks merge with user and project hooks, and all matching hooks run in parallel. Hookify finds its rules with glob('.claude/hookify.*.local.md') relative to the hook process's current directory.** [high]
  hookify's hooks.json registers PreToolUse, PostToolUse, Stop and UserPromptSubmit with no matcher. Each runs `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/<event>.py"` with a 10s timeout, so a python3 process spawns on every tool call. Hookify's own repo .gitignore marks `.claude/*.local.md` as 'should not be committed'. A worktree is a fresh checkout, so the rule files exist there only if committed or, when gitignored, listed in .worktreeinclude. If the session cd's into a subdirectory, the relative glob finds nothing.
  Source: <https://github.com/anthropics/claude-plugins-official/blob/main/plugins/hookify/core/config_loader.py>
- **The Learning output style marks spots with TODO(human), then stops and waits for you, so it would stall unattended runs. It applies to the main conversation and forks, not to regular subagents.** [high]
  Set it with `outputStyle` (case-sensitive: "Learning") or /output-style. Auto mode's nudge to keep working doesn't apply when the prompt relies on user input, and /goal stops its loop after several no-tool turns. Forks inherit the parent's system prompt, and fork mode is on by default interactively. Use Default, Proactive or Concise for autonomous sessions and switch to Learning only in hands-on sessions.
  Source: <https://code.claude.com/docs/en/output-styles.md>

### Exact snippets (copied from the sources named)

**Project .claude/settings.json: plugins, model/effort, concurrency, permissions, hooks (commit this)** — <https://code.claude.com/docs/en/settings-reference.md>

```
{
  "model": "opus",
  "effortLevel": "high",
  "fallbackModel": ["sonnet", "haiku"],
  "env": {
    "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "4",
    "CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS": "4"
  },
  "extraKnownMarketplaces": {
    "octen": { "source": { "source": "github", "repo": "Octen-Team/octen-mcp" } }
  },
  "enabledPlugins": {
    "hookify@claude-plugins-official": true,
    "frontend-design@claude-plugins-official": true,
    "pydantic-ai@claude-plugins-official": true,
    "logfire@claude-plugins-official": true,
    "firecrawl@claude-plugins-official": true,
    "octen@octen": true
  },
  "permissions": {
    "allow": [
      "Bash(uv sync *)", "Bash(uv add *)", "Bash(uv lock *)",
      "Bash(uv run pytest *)", "Bash(uv run ruff *)",
      "Bash(git add *)", "Bash(git commit *)", "Bash(git switch *)", "Bash(git fetch *)",
      "Bash(git push -u origin *)",
      "Bash(gh pr create *)", "Bash(gh pr view *)", "Bash(gh pr checks *)",
      "Bash(gh run list *)", "Bash(gh run view *)"
    ],
    "deny": [
      "Read(./.env)", "Read(./.env.*)",
      "Bash(git push --force *)", "Bash(git push -f *)", "Bash(git push * main)",
      "Bash(git reset --hard *)", "Bash(gh repo delete *)"
    ]
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/ruff-after-edit.sh",
            "args": [],
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

**.claude/hooks/ruff-after-edit.sh (chmod +x, commit; reads file_path from stdin JSON, works from any worktree)** — <https://code.claude.com/docs/en/hooks.md>

```
#!/bin/bash
f=$(jq -r '.tool_input.file_path // empty')
case "$f" in *.py) ;; *) exit 0 ;; esac
root=$(git -C "$(dirname "$f")" rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0
uv run --frozen ruff format "$f" >/dev/null 2>&1
if ! out=$(uv run --frozen ruff check --fix "$f" 2>&1); then
  echo "$out" >&2
  exit 2   # PostToolUse exit 2 = stderr shown to Claude so it fixes remaining lint
fi
exit 0
```

**Exec-form hook shape from the docs** — <https://code.claude.com/docs/en/hooks.md>

```
{
  "type": "command",
  "if": "Bash(rm *)",
  "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-rm.sh",
  "args": []
}
```

**User ~/.claude/settings.json (auto mode can't come from project files)** — <https://code.claude.com/docs/en/permission-modes.md>

```
{
  "permissions": { "defaultMode": "auto" },
  "askUserQuestionTimeout": "5m"
}
```

**Per-machine plugin install for external-source plugins (run once after cloning)** — <https://code.claude.com/docs/en/plugins/install.md>

```
claude plugin marketplace add anthropics/claude-plugins-official   # only needed if no interactive session has run on this machine yet
claude plugin install pydantic-ai@claude-plugins-official --scope project
claude plugin install logfire@claude-plugins-official --scope project
claude plugin install firecrawl@claude-plugins-official --scope project
claude plugin install neon@claude-plugins-official --scope project      # phase 2
claude plugin install vercel@claude-plugins-official --scope project    # phase 2
claude plugin marketplace add Octen-Team/octen-mcp --scope project
claude plugin install octen@octen --scope project
claude plugin list
```

**Octen MCP without the plugin (alternative)** — <https://github.com/Octen-Team/octen-mcp>

```
claude mcp add --transport http octen https://mcp.octen.ai/mcp --header "x-api-key: your-key-here"
```

**Subagent definition .claude/agents/implementer.md** — <https://code.claude.com/docs/en/sub-agents.md>

```
---
name: implementer
description: Implements one scoped Phase 1 task in its own worktree, runs tests, opens a PR
model: claude-sonnet-5-5
effort: high
isolation: worktree
---
Implement the assigned task, run `uv run pytest -q` and `uv run ruff check .`, commit on a feature branch, push, and open a PR with gh pr create.
```

**Force one model onto all subagents (otherwise the env var is only a default)** — <https://code.claude.com/docs/en/sub-agents.md>

```
{
  "env": {
    "CLAUDE_CODE_SUBAGENT_MODEL": "haiku",
    "CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"
  }
}
```

**.worktreeinclude (copies only files that are gitignored AND match)** — <https://code.claude.com/docs/en/worktrees.md>

```
.env
.claude/hookify.*.local.md
```

**Recommended /goal line** — <https://code.claude.com/docs/en/goal.md>

```
/goal Phase 1 is done: `uv run pytest tests/acceptance -q` exits 0 with every Phase 1 acceptance test passing and none skipped or xfailed, `uv run ruff check .` and `uv run ruff format --check .` exit 0, and no file under tests/acceptance/ was modified; print each command's final output in the transcript as proof; or stop after 60 turns
```

**Recommended /loop line** — <https://code.claude.com/docs/en/scheduled-tasks.md>

```
/loop 15m run `gh run list --branch main --limit 3`; if the newest run on main failed, read `gh run view <id> --log-failed`, fix the root cause on a new branch in a worktree, push it and open a PR with `gh pr create`, then report the PR URL; if CI is green or a fix PR is already open, do nothing and say so
```

**Command used to verify official marketplace entries** — <https://github.com/anthropics/claude-plugins-official>

```
gh api repos/anthropics/claude-plugins-official/contents/.claude-plugin/marketplace.json --jq '.content' | base64 -d
```

### Recommendations
- Commit `enabledPlugins` and the Octen `extraKnownMarketplaces` entry in .claude/settings.json. Add a README/bootstrap step that runs the `claude plugin install <name>@claude-plugins-official --scope project` lines, because external-source plugins (pydantic-ai, logfire, firecrawl, neon, vercel, tavily) are never auto-installed from project settings.
- Open the repo interactively once and accept the trust dialog before any unattended or -p run. Until then, project allow rules, repository marketplaces, project subagent hooks and `claude -w` are ignored or refused.
- Don't set `permissions.defaultMode` in the committed project file, since anything other than auto would override the built-in auto default. Put `"defaultMode": "auto"` and `askUserQuestionTimeout` in ~/.claude/settings.json, and pass `--permission-mode auto` explicitly for any `claude -p` run.
- Use deny rules rather than ask rules for things you want blocked during unattended runs. In auto mode, ask rules on command content fall back to a prompt and stall the run.
- Pin subagent models in frontmatter using full IDs (claude-sonnet-5-5, claude-opus-5-5, claude-haiku-5-5). Avoid `fable` for unattended background work unless you have accepted the usage-credit billing, and set `fallbackModel` in settings so overload errors don't kill subagents.
- Use CLAUDE_CODE_SUBAGENT_MODEL only as a default; add CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1 if you truly want one model everywhere. Check the result with /tasks while agents run.
- On a 24 GB Mac, cap concurrency through settings env (for example 4 subagents and 4 workflow agents) instead of the defaults of 20 and 16. Each worktree gets its own uv .venv and pytest processes.
- Decide how merging will happen before relying on auto-merge. The auto-mode classifier blocks merging PRs that no human approved by default. Either approve and merge yourself, enable GitHub-native auto-merge with branch protection outside Claude, or add a narrowly worded `autoMode.allow` entry in user settings after checking `claude auto-mode defaults`.
- If hookify rules must apply inside worktrees, commit the `.claude/hookify.*.local.md` files (or list them in .worktreeinclude if gitignored). Make sure `python3` is on PATH for the hook process; on this machine it is the uv shim at ~/.local/bin/python3.
- Add `.claude/worktrees/` to .gitignore. Set `worktree.baseRef: "head"` only if subagents must build on unmerged local commits; the default 'fresh' base is origin's default branch.
- Keep the Learning output style out of committed settings. Use `/output-style Learning` only in hands-on study sessions, and Default, Proactive or Concise for /goal-driven autonomous sessions.
- Treat /goal and /loop as attended conveniences: keep the terminal session open, or background it (which carries /loop tasks over), and recreate loops before the 7-day expiry. Use GitHub Actions or Routines for anything that must outlive the session.

### Risks
- Auto-merge conflict: the classifier's default rule against merging PRs no human has approved will block or stall `gh pr merge` in auto mode, and after 3 consecutive or 20 total blocks auto mode reverts to prompting.
- Public repo exposure: committed .claude/settings.json, CLAUDE.md, hook scripts and PR bodies are public. Never put secrets in the settings `env` block (github plugin PAT, OCTEN key, Neon URL), and expect the classifier to block PR or commit text that contains internal paths or live data.
- Fresh clones and CI won't have external-source plugins unless someone runs `claude plugin install ... --scope project`. In -p runs plugins install in the background and can be missing on the first turn without CLAUDE_CODE_SYNC_PLUGIN_INSTALL=1.
- Fable usage-credit consent prompts in background sessions expire after 5 minutes and end the turn without sending, and Fable usage may bill extra credits on a solo plan.
- Safety-classifier fallback (cyber/bio flags) can silently move subagents to Opus 4.8, Opus 5 or Sonnet 5, which makes the model shown in frontmatter differ from what actually ran; check /tasks.
- Writes to .claude/** (agents, hooks, hookify rules), .pre-commit-config.yaml, .vscode and .mcp.json are protected paths. Allow rules never pre-approve them, so in acceptEdits they prompt and in auto they depend on the classifier.
- Hookify spawns python3 for every tool call with no matcher, which adds latency across many parallel agents. Its relative `.claude/` glob silently matches nothing if the hook runs from a subdirectory or from a worktree that lacks the rule files.
- Subagent worktrees branch from origin's default branch by default, so a subagent won't see the parent's uncommitted or unpushed work unless worktree.baseRef is 'head'.
- Default concurrency (20 subagents, 16 workflow agents) plus a uv environment per worktree can exhaust 24 GB RAM.
- /loop stops when the session closes, never catches up missed fires, and doesn't restore self-paced loops on resume. /goal clears on auth, credit, context-overflow or model-unavailable errors and pauses on usage limits.
- Bash allow prefixes for environment runners (for example `uv run *`) effectively allow arbitrary commands, and Bash deny rules don't stop alternate invocations such as /usr/bin/git or `sh -c`.

### Open questions
- Is the default 'merging a pull request no human has approved' classifier rule a soft_deny (overridable by a user `autoMode.allow` entry or explicit intent) or a hard_deny? The permission-modes page doesn't say; `claude auto-mode defaults` prints it (not run here, to stay read-only).
- Does a hook `if` of "Edit(**/*.py)" match Write tool calls? The permissions docs say Edit rules cover all file-editing tools, but the hooks page doesn't say so explicitly. The snippet above filters inside the script instead.
- What is the hook process's working directory for tool calls made by a subagent running with `isolation: worktree`? The docs say handlers 'run in the current directory' and `cwd` follows Claude into worktrees, but don't address isolated subagents explicitly. This determines whether hookify reads that worktree's .claude/ files.
- Does the /workflows progress view show each workflow agent's model? Not stated in the workflows page.
- Does the Fable usage-credit consent prompt also trigger for a subagent with `model: fable` spawned from an interactive main session on the user's plan?
- Does declaring `claude-plugins-official` itself in a project's extraKnownMarketplaces behave identically to the auto-added registration? Not tested; it was left out of the snippet.
- Pydantic AI 2.56 compatibility of the pydantic-ai and logfire plugins was not checked in this topic.
