# Task: an agent-assisted pull request, from issue to merge

You will connect the GitHub MCP server to Claude Code in read-only mode. Then you write an issue, let an agent make a pull request for it, review it yourself, and merge it under the ruleset from GH8. At the end you remove the token again.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. The repo needs the `protect-main` ruleset (GH1 and GH8) and your `checks` workflow (GH2), so that the pull request has real rules to meet. If you do not have them yet, stop here and do those lessons first. The checker below needs the repo.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code. You need Claude Code installed (see GH10). If you do not have it, you can do the agent's part by hand: the checker looks at your issue and pull request on GitHub, and it cannot tell who typed the commits.

**Never paste your token into a chat with the agent, into a file you commit, or into an issue or pull request.**

## 1. Make a token that can only read your practice repo

1. In your browser, open GitHub, then **Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token**. The page may be renamed, so use the search box in Settings if you do not see it.
2. Give it a name such as `hint-kata-mcp`, and a short expiry, such as 7 days.
3. Under **Repository access**, choose **Only select repositories** and pick your practice repo and nothing else.
4. Under **Repository permissions**, set **Contents**, **Issues** and **Pull requests** to **Read-only**. Leave everything else at no access.
5. Create the token and copy it once. GitHub shows it only once.

## 2. Save it in a local file that git ignores

1. Open your practice repo folder in VS Code (**File > Open Folder**) and open the terminal (**View > Terminal**).
2. Tell git to ignore the two files in this folder only. This writes to a file inside `.git`, so nothing is committed:

```bash
printf '.env\n.mcp.json\n' >> .git/info/exclude
```

3. Create a file named `.env` in the folder. Put one line in it, with your token after the equals sign:

```text
GITHUB_PAT=paste-your-token-here
```

4. Run `git status`. Neither `.env` nor `.mcp.json` should show up. If `.env` shows up, stop and fix step 2 before you go on.

## 3. Connect the server, read-only

Run these in the terminal, not inside a Claude Code session. They use the default `local` scope, so the setting is only yours:

```bash
export GITHUB_PAT="$(grep '^GITHUB_PAT=' .env | cut -d '=' -f2-)"
claude mcp add-json github '{"type":"http","url":"https://api.githubcopilot.com/mcp/readonly","headers":{"Authorization":"Bearer '"$GITHUB_PAT"'"}}'
claude mcp list
```

The list should show a server named `github`. Now the token is saved in Claude Code's own settings, so you do not need the `.env` file any more. Delete it and clear the variable:

```bash
rm .env
unset GITHUB_PAT
```

Never add `--scope project` to this command. If `claude mcp add-json` answers `Invalid input` on Windows, use `claude mcp add --transport http github https://api.githubcopilot.com/mcp/readonly -H "Authorization: Bearer $GITHUB_PAT"` instead, and keep the default scope.

## 4. Write the issue

Make a small issue with one clear job. Run this inside the practice repo folder:

```bash
gh issue create --title "Add a note about MCP to the README" --body "Add a section titled '## Notes' to README.md with one sentence that says what MCP stands for. Do not change any other file."
```

`gh` prints the issue address, which ends with the issue number. Write the number down. The steps below call it `<n>`.

## 5. Let an agent do the work

1. In the same terminal, start Claude Code with `claude`.
2. Check the connection with the `/mcp` command. You should see `github` as connected. If it is not, stop and fix the connection first.
3. Give the agent this job. Replace `<n>` with your number:

```text
Read issue <n> of this repo using the GitHub MCP server. Then, using git and gh in this terminal: make a branch named issue-<n>-mcp-note, do what the issue asks and nothing more, commit, push the branch, and open a pull request whose body ends with the line "Closes #<n>". Do not push to main. Do not merge anything. Do not read or print any token.
```

4. Read what the agent proposes before you approve each command. Look for the GitHub tool call that reads the issue. This is the MCP server at work. If the agent asks to push to `main` or to merge, say no.
5. When it finishes, quit Claude Code.

## 6. Review it yourself, then merge

Use the five questions from GH10: size, scope, tests, secrets, and whether the pull request text explains itself. Replace `<pr>` with the pull request number the agent gave you:

```bash
gh pr view <pr> --json additions,deletions,changedFiles
gh pr view <pr> --json files --jq '.files[].path'
gh pr diff <pr>
gh pr checks <pr> --watch
```

Only one file should change, `README.md`. If the agent touched anything else, close the pull request, say why in a comment, and try again with a tighter prompt. If it is right and `checks` is green, you merge. The agent does not:

```bash
gh pr merge <pr> --squash --delete-branch
```

Check that the issue closed because of the pull request:

```bash
gh issue view <n> --json state,stateReason,closedByPullRequestsReferences
```

You should see the state `CLOSED`, the reason `COMPLETED`, and your pull request in the list.

## 7. Clean up

1. Remove the server from Claude Code: `claude mcp remove github`.
2. In the browser, go back to **Fine-grained tokens** and delete the token. A token you do not use is a risk you do not need.
3. Run `git pull` on `main`, and run `git status` once more to check that no `.env` or `.mcp.json` is left.

## Check my work

Set `PRACTICE_REPO` in `.env` of the Hint Kata app, then press **Check my work**. It runs read-only `gh` calls:

- A pull request from a branch other than `main` was merged into `main`, and it closes at least one issue.
- At least one issue is closed as completed, and a pull request is recorded as the closer.
- The rules on `main` still include a pull request rule, so the work went through the ruleset.
- No `.mcp.json` or `.env` file is committed anywhere in the repo.

The checker cannot see which tool made the commits, or whether you used the MCP server. Those are on your honour. The point of the task is the habit: a narrow token, a branch, a pull request, a review, and a person who merges.
