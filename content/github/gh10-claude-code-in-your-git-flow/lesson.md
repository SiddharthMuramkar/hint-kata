---
id: gh10-claude-code-in-your-git-flow
track: github
title: "Claude Code in your local git flow"
minutes: 30
pins:
  gh: "2.102"
  claude-code: "2.1.x"
sources:
  - claude-code-docs-memory
  - claude-code-docs-worktrees
  - claude-code-docs-common-workflows
  - claude-code-docs-permissions
  - claude-code-docs-best-practices
  - claude-code-docs-permission-modes
  - claude-code-docs-hooks
---
Claude Code is a program that reads your code, edits files and runs commands in your terminal. In this lesson you use it inside the git flow you already know: a branch, a commit, a push and a pull request. The new question is not how to make it write code. It is how to let an agent work without trusting it blindly. This repo, Hint Kata, is built that way, so you read its real files: `CLAUDE.md`, the `.claude/` folder and `docs/HARNESS.md`. The Claude Code documentation is linked, not reproduced. Every explanation here is written in our own words from this repo's setup, and each documented fact has a link to the page that states it. This site is not affiliated with Anthropic or GitHub.

One idea runs through it all. An instruction is a request, but a rule that a program enforces is a lock. Use requests to steer the agent, and locks to keep it safe.

## What memory files are for

A new Claude Code session starts with an empty context window. Yesterday's chat is not in it. What carries over is files: your `CLAUDE.md` and rules files, which you write, and the notes Claude writes for itself, called auto memory. `CLAUDE.md`, rule files without a `paths:` line, and auto memory are loaded at the start of a session; path-scoped rule files load later, when Claude touches matching files. A session you reopen with `--continue` or `--resume` keeps its transcript too. So for anything that must survive a cut-off, write it down in a file. ([How Claude remembers your project](https://code.claude.com/docs/en/memory))

This repo keeps four things in files for that job.

- **`CLAUDE.md`** at the repo root. It is read at the start of every session. Ours had 61 lines on 2026-10-14: the stack and its pinned versions, the six commands to run, the repo layout, the model routing, the rules for PRs, and a rule about secrets. The docs target under 200 lines per file, because a longer file costs more context and gets followed less well. Keep it for things Claude cannot work out from the code. ([Memory: CLAUDE.md size](https://code.claude.com/docs/en/memory))
- **`.claude/rules/*.md`**: one topic per file, here `python.md`, `agents.md`, `content.md` and `git.md`. A rule file with a `paths:` line at the top, such as `paths: ["content/**"]`, is only loaded when Claude works on matching files. A rule file without one is loaded at the start, like `CLAUDE.md`. So lesson-writing rules stay out of the way when you edit app code. ([Memory: rules](https://code.claude.com/docs/en/memory))
- **`.claude/agents/*.md`**: one file per helper agent. Each has a short header (`name`, `model`, `effort`, `tools`) and a body that says what the helper does. We have `builder`, `content-writer`, `diff-reviewer` and `second-opinion`. These files are not memory in the docs' sense. They define helpers, but they are files in the repo that a new session can read. The reviewer is not allowed to edit files (`disallowedTools: Edit, Write, NotebookEdit`), so it can only read and report.
- **A "Resume here" section** inside `CLAUDE.md`. After a cut-off, a new session reads `docs/RESUME.md` and `docs/PROGRESS.md`, then runs `git status`, `git worktree list` and `gh pr list --state open`. That is the whole trick: the state of the work lives in files and in git, not in the chat.

Now the limit. A memory file only asks. The permissions page says plainly that guidance in `CLAUDE.md` shapes what Claude tries, and does not enforce a boundary. ([Configure permissions](https://code.claude.com/docs/en/permissions)) So this repo says "never read `.env`" in `CLAUDE.md`, and then says it again in places that do enforce it, which you meet in the guard-rails section below.

## Worktrees for parallel work

A git worktree is a second folder that shares one repository. Each folder has its own branch checked out, and all of them share the same history. You can run this in any repo. It makes a new branch and a new folder in one step:

```bash
git worktree add -b claude/first-change ../demo-claude
git worktree list
```

On 2026-10-14 I ran this in a throwaway repo. The list showed both folders, one on `main` and one on `claude/first-change`. A commit made in the second folder did not move `main`. Git also refused to check out `claude/first-change` in the first folder while the second one held it, and it printed that the branch was already used by that worktree. One branch can be checked out in only one worktree at a time. When you are done, `git worktree remove ../demo-claude` deletes the folder and keeps the branch.

Why does an agent need this? Two agents that edit one folder step on each other's files and commit each other's half-done work. Give each agent its own folder and its own branch, and they can run side by side. Claude Code does this in two ways.

- **By hand:** `claude --worktree <name>` (or `-w`). By default it makes the folder `.claude/worktrees/<name>/` on a new branch named `worktree-<name>`. ([Worktrees](https://code.claude.com/docs/en/worktrees)) On 2026-10-14 I checked that `claude --help` for version 2.1.299 lists `-w, --worktree`.
- **From an agent file:** `isolation: worktree` in the header. Our `builder` and `content-writer` agents have it, so every task they start gets a fresh folder.

Some facts about this repo's setup:

- `.claude/worktrees/` is listed in `.gitignore`, so the folders never end up in a commit. The hookify rule files in `.claude/` are committed on purpose, so every worktree has the guard-rails too.
- `.worktreeinclude` lists the gitignored files to copy into each new worktree. Ours names the local env file that holds the owner's keys. That is handy, because the app needs it to run. It also means one more copy of a secret on your disk. That is a reason for the deny rules in the next section.
- A new worktree is a plain checkout with no installed packages. Each one needs its own `uv sync` and gets its own `.venv`. Folders add up in RAM and disk, which is why `settings.json` caps parallel agents (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=3`) and `docs/HARNESS.md` says to run at most two worker worktrees at a time.
- Hook scripts keep running from the main checkout in a worktree. `${CLAUDE_PROJECT_DIR}` still points at the project root, and the folder Claude is working in is passed to the hook separately. ([Worktrees](https://code.claude.com/docs/en/worktrees)) You can see how our `ruff_after_edit.py` copes: it asks git for the top folder of the edited file, so it formats the file where it lives.
- `git worktree list` shows every folder, and `git worktree remove` cleans one up. `CLAUDE.md` tells a new session to run the list first, in case a half-finished worktree is waiting.

## Guard-rails with permissions and hooks

Agents here run with the owner's own GitHub login. That is powerful, so the guard-rails matter. There are three layers: permission rules, hooks, and the GitHub ruleset. Each one catches things the others miss.

**Permission rules** live in `.claude/settings.json`. The `allow` list names commands that run without a prompt: `uv run pytest *`, `git add *`, `git commit *`, `git push -u origin *`, `gh pr create *`, `gh pr merge --auto *`, and the other named tools: `git switch *`, `git worktree *`, `gh issue *`, `uv sync *`, `uv lock *` and some read-only `git` and `gh` views. The `deny` list names commands that never run. Ours falls into four groups:

- **Dangerous basics:** `sudo`, `git push --force`, `git push -f`, `git reset --hard`.
- **Repo admin:** `gh repo delete`, `gh repo edit`, `gh api -X DELETE`, `-X PATCH` and `-X PUT`, and `gh pr merge --admin`. The login is an admin login, so these make it harder for an agent to loosen the repo's own protection.
- **Secrets:** `gh secret *`, and `Read` on the env files, with `!.env.example` as a carve-out so the names-only example file can still be read.
- **The guard-rails themselves:** `Edit` on `.claude/settings*.json`, `.claude/hooks/**` and `.claude/hookify.*`. An agent cannot quietly switch off the fence around it.

The documented evaluation order is deny first, then ask, then allow, and the first match wins. ([Configure permissions](https://code.claude.com/docs/en/permissions)) A deny rule also beats a hook that says "allow".

Why deny rules, and not ask rules? An ask rule stops and waits for a person to click yes. In an unattended run there is no person, so the run just waits. `docs/HARNESS.md` records that ask rules stall in auto mode here, so the rule is: safe things go in `allow`, harmful things go in `deny`, and nothing is left to ask. A deny answers at once, and the agent has to find another way.

A note on prompts. From Claude Code 2.1.283, the starting permission mode in a terminal session is auto mode. A separate classifier model reviews actions, and most commands run with no prompt at all. ([Best practices](https://code.claude.com/docs/en/best-practices)) The mode that asks about each action is called Manual. You switch to it by pressing `Shift+Tab` until the status bar shows manual mode, or by starting with `claude --permission-mode manual` (the docs also accept `default`, which is the config value for the same mode). ([Choose a permission mode](https://code.claude.com/docs/en/permission-modes)) Auto mode replaces prompts with a classifier. It does not remove the locks. Deny rules block in every mode, and hooks still run. On 2026-10-14 I checked that `claude --help` for 2.1.299 lists `manual` and `auto` among the `--permission-mode` choices, and that the flag also accepted `default`. The task below asks you to use Manual mode, so that you see each command.

Allow rules need care too. This repo never allows `Bash(uv run *)`. On 2026-10-14 I checked that `uv run echo hi` and `uv run python -c "..."` both run, because `uv run` starts whatever program follows it. An allow rule on that prefix would allow every command. So the list names exact tools: `uv run pytest *`, `uv run ruff *`, `uv run ty *`, and so on.

**Hooks** are small programs that run at fixed moments. The docs call them deterministic, unlike `CLAUDE.md` text, which is advisory. ([Best practices](https://code.claude.com/docs/en/best-practices)) The repo has two kinds.

- **A settings hook**, `ruff_after_edit.py`. After every edit to a `.py` file it runs `ruff format` and `ruff check --fix`. If errors remain, it exits with code 2 and prints them, and Claude sees them and fixes them. A second script, `session_end.py`, copies the session transcript out of the repo, but it is not switched on yet.
- **Eight hookify rules**, in files named `.claude/hookify.<name>.local.md`. Six of them match the Bash command with a regex `pattern`. The other two, `block-env-edit` and `stop-run-tests`, use `conditions:` on a file path and on the session transcript. When a rule matches, the action is blocked, and the message in the file tells Claude why.

| Rule | It blocks |
|---|---|
| `block-sudo` | `sudo` at the start of a shell command |
| `block-rm-rf` | `rm -rf` and its flag variants |
| `block-force-push` | `git push` with `-f` or `--force` |
| `block-push-main` | `git push` to `main` or `master` |
| `block-env-bash` | reading the env file with `cat`, `grep`, `source` and similar (the example file is fine) |
| `block-env-edit` | editing any env file except the example file |
| `block-print-secrets` | `printenv`, a bare `env`, `echo $SOMETHING_KEY` |
| `stop-run-tests` | stopping a session before `pytest` appears in the transcript |

On 2026-10-14 I ran each pattern against sample commands, the way hookify applies them (a case-insensitive search). Results: `git push origin main` is blocked; `git push -u origin claude/first-change` is allowed; `git push -u origin x && gh pr create --base main` is allowed; `cat .env` is blocked (by `block-env-bash`, and `block-print-secrets` also matches it, because its bare `env` branch matches the `env` at the end of `.env`, which is harmless); `cat .env.example` is allowed. One more result shows why the next rule exists. A heredoc (a multi-line text block in a shell command) that merely contains the words `git push origin main` is blocked, because the pattern searches the whole command text. So run `git push` as its own command, and do not write blocked words in the text of a command.

Hooks and deny rules still have gaps. The permissions page lists some: a Bash rule for `git push *` does not catch `git -C . push`, `git 'push'` or `sh -c '...'`, and a rule for `curl` or `rm` can miss `/usr/bin/curl` or `/bin/rm`. By the same logic, a path form such as `/usr/bin/git push` could slip past a rule written for `git push`. That last one is my own extrapolation, not an example on the page. Also, `stop-run-tests` is a rule on the Stop event, and the [hooks reference](https://code.claude.com/docs/en/hooks) lists SubagentStop as a separate event for helper agents. So I expect `stop-run-tests` to guard the main session only. I did not test that. So the last lock is not on your machine. It is the GitHub ruleset. On 2026-10-14 I read this repo's ruleset with `gh api`: it is called `protect-main`, it is active, it has no bypass actors, and its rules are deletion, non-fast-forward, pull request (squash merges only) and required status checks. No push gets past the ruleset, not even an admin's. But an admin login can edit or delete the ruleset itself. The deny list tries to stop that (`gh api -X DELETE/PATCH/PUT`), and those deny rules have the same prefix gaps as above, for example `--method DELETE` or `-X` written after the path. So the ruleset is the strongest lock, not an unbreakable one. That is why GH1 and GH7 come before this lesson.

## How Claude opens a branch and a pull request

Claude does not have a special way to use git. It runs the same commands you do, and your permission rules decide which ones need no prompt. The whole path, as the `builder` agent follows it:

```bash
git fetch origin
git switch -c claude/first-change origin/main
# Claude edits files, then:
git add notes.md
git commit -m "docs: add a note"
git push -u origin claude/first-change
gh pr create --base main --title "docs: add a note" --body-file pr.md
```

Run `git push` as its own command, for the reason in the last section. `gh pr create` has `--base` for the target branch, `--title`, and either `--body` or `--body-file` for the text. `--fill` takes the title and body from your commits, and `--draft` opens a draft. On 2026-10-14 I checked these against `gh pr create --help` for `gh` 2.102. When Claude opens a PR with `gh pr create`, Claude Code links the session to that PR, so you can find the conversation later. ([Common workflows](https://code.claude.com/docs/en/common-workflows))

This repo has a house style on top of that. One issue, one branch named `issue-<n>-<slug>`, one PR, one worktree. The commit ends with a `Co-Authored-By` line. The PR body is plain English: what changed, why, and which file to read first. It ends with `Closes #<n>` and the line `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. That line is a label that tells readers who wrote the change. It proves nothing, because anyone can type it. Your practice task below uses the branch prefix `claude/` instead, so the checker can find it.

Then a human takes over. The ruleset says the change can only reach `main` through a pull request, with the `checks` job green and a squash merge. Nobody can push to `main` directly, not even an admin. (An admin could still edit the ruleset itself, as the last section said.) In a repo with a second person you would also require an approving review. Here the ruleset asks for zero approvals, because there is one owner, so the review is the owner reading the diff before pressing merge. The next two sections are about doing that well.

## The loop in this repo, with real pull requests

`docs/HARNESS.md` and `docs/RESUME.md` describe the loop for one task:

1. The `builder` takes one issue in its own worktree, writes the change and tests, runs ruff, ty and pytest, and opens the PR. It does not merge.
2. The `diff-reviewer` agent reads the diff with fresh eyes, looking at scope, tests, secrets and attribution, and returns a list. It is a separate agent because a reviewer that did not write the code is less biased toward it. ([Best practices](https://code.claude.com/docs/en/best-practices))
3. The builder fixes what the reviewer found and pushes more commits to the same branch. The PR updates itself.
4. When the review is clean and CI is green, `gh pr merge --auto --squash` is armed, and GitHub merges when the last check passes. Plain `--auto` is allowed by `settings.json`. `--admin` is denied.
5. The PR body is also saved as one new file in `docs/learning-log/`. That file is the record you can read later.

Three real pull requests in this repo show it (numbers as of 2026-10-14).

- **#69, a small one.** It changed 4 files, 47 lines added and 5 removed, in one commit. Two hookify rules blocked harmless commands: `block-env-bash` matched the end of a sentence inside an issue text, and `block-push-main` matched `gh pr create --base main` in the same command as a push. The fix limited each pattern to one shell segment. The lesson in it: the guard-rails have bugs too, and a PR fixes them like any other code. Auto-merge was armed with a squash.
- **#106, a fix after a scanner spoke.** A path check in `app/checker.py` was flagged by CodeQL. The PR has four commits. The first was a correct check that CodeQL still did not accept. The second changed it to `os.path.realpath` plus a string `startswith`, which CodeQL does accept. The third made unknown lesson ids return 404. The fourth merged `main` in. It merged with `checks` and all four CodeQL jobs green. The lesson in it: a green first try is not the norm, and the loop is built to expect fix commits.
- **#105, a big one.** It changed 24 files with about 2,400 added lines. Its commits include a CodeQL fix and one named "review fixes for #105". That is the loop working at a larger size. Size is a reason to read more slowly, not a reason to say no.

## Checking an agent pull request before you merge

A green check is not a review. The check says the tests that exist passed. It does not say the change is the right size, or safe, or on topic. Before you merge an agent's PR, go through five things. Every one has a command.

1. **Size.** Does the number fit the issue? `gh pr view 105 --json additions,deletions,changedFiles`. One-line request, 2,000-line diff: stop and ask why.
2. **Scope.** Is every changed file one the issue would touch? `gh pr view 105 --json files --jq '.files[].path'`. Look for scope creep: renamed things, "while I was there" fixes, new dependencies. Look hardest at the guard-rail paths: `.claude/settings.json`, `.claude/hooks/`, `.claude/hookify.*`, and `.github/workflows/`. Those lines decide what the next agent may do. Our deny list stops an agent editing the first three, but workflow files are deliberately not denied, so CI changes get reviewed in the PR. A diff that touches them is fine when the issue asks for it, as #69 did, and then you read every line. For a workflow, check the `permissions:` block and any new secret, as in GH5. Also remember that an edited workflow can change what `checks` itself does, so a green result from edited CI proves less.
3. **Tests.** Did new behaviour get a new test? Were any tests deleted, skipped or loosened to make CI pass? `gh pr checks 105` shows the result, and the diff shows whether the tests are real.
4. **Secrets and personal details.** Search the diff: `gh pr diff 105 | grep -n -i -E "key|token|secret|password|/Users/"`. On 2026-10-14 this search found ten lines on #69, because that PR's text talks about secrets. A hit is a prompt to read the line, not a verdict. Secret scanning and push protection are safety nets for known kinds of secret, not promises (see GH5). If a real secret got in, rotate it first. Deleting the commit is not enough.
5. **The PR text.** Is the body plain English and does it say what changed and why? Does it end with `Closes #<n>`? Is there exactly one new learning-log file, and no edit to `docs/PROGRESS.md`? A PR that cannot explain itself is hard to trust.

If all five are fine, squash merge. If one is not, comment on the PR and send it back to the builder. Do not fix it quietly yourself, and do not use `--admin` to get around a failing check.

Done by hand, the branch-and-PR path is identical. Claude Code is optional for the task below.

Claude Code docs are linked only (no reuse licence); everything else is this repo's own material. This site is not affiliated with Anthropic or GitHub. Checked with `gh` 2.102 and Claude Code 2.1.299, 2026-10-14.

**Sources (linked, not reproduced):**
[How Claude remembers your project](https://code.claude.com/docs/en/memory),
[Run parallel sessions with worktrees](https://code.claude.com/docs/en/worktrees),
[Common workflows](https://code.claude.com/docs/en/common-workflows),
[Configure permissions](https://code.claude.com/docs/en/permissions),
[Best practices for Claude Code](https://code.claude.com/docs/en/best-practices),
[Choose a permission mode](https://code.claude.com/docs/en/permission-modes),
[Hooks reference](https://code.claude.com/docs/en/hooks).
