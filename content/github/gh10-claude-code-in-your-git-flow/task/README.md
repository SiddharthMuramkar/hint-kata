# Task: let Claude Code make a branch and a pull request

You will ask Claude Code to make a branch called `claude/first-change`, make one commit, push the branch and open a pull request in your practice repo. Then you review the diff like the lesson says. You do **not** merge it. If Claude Code is not installed on your machine, you do the same steps by hand. Both ways count.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. It must be a public repo, with the `checks` workflow from lesson GH2 so a CI run happens on the pull request. If you do not have those yet, stop here and do GH1 and GH2 first. The checker below needs them.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code.

**Secret rule.** Never paste a key, token or password into Claude Code, into a file, or into the pull request. The repo is public.

## 1. Open the repo and update main

1. In VS Code, choose **File > Open Folder** and open your practice repo folder.
2. Open the terminal with **View > Terminal**.
3. Run:

```bash
git switch main
git pull
claude --version
```

If `claude --version` prints a version number, go to step 2A. If the command is not found, Claude Code is not installed. Go to step 2B. Installing it is up to you. The install page is in the Claude Code docs, and the account sign-in is something only you can do.

## 2A. With Claude Code

1. Start it in Manual mode, so that it asks before each command: `claude --permission-mode manual`. (Since version 2.1.283 the normal starting mode is auto mode, where a classifier reviews actions and most commands run with no prompt. For this task you want to see every command.) If it asks whether you trust the folder, read the question and answer for your own repo only. If you started it with plain `claude`, press `Shift+Tab` until the status bar at the bottom shows manual mode.
2. Paste this prompt:

```text
Make a new branch called claude/first-change from main. Add a file called notes-gh10.md with three
short lines that say what this repo is for. Make one commit with a clear message. Push the branch
with git push -u origin claude/first-change. Then open a pull request into main with gh pr create.
The pull request body must say what changed and end with the line "Generated with Claude Code".
Do not merge it.
```

3. In Manual mode, Claude Code asks permission before it runs commands. Check that the status bar still shows manual mode, then read each command before you accept. Say no to anything that touches a secret, pushes to `main`, or merges. If it tries `git push origin main`, decline and tell it to use the branch.
4. When it prints the pull request address, you can leave Claude Code with `/exit`.

## 2B. By hand, if Claude Code is not installed

```bash
git switch -c claude/first-change
```

Create a file called `notes-gh10.md` with three short lines that say what the repo is for. Then:

```bash
git add notes-gh10.md
git commit -m "docs: add notes for GH10"
git push -u origin claude/first-change
gh pr create --base main --title "docs: add notes for GH10" --body "Adds a short notes file.

Written by hand, because Claude Code is not installed."
```

The checker only looks for the words "Claude Code" in the body. The line above says the truth, and it passes. Do not write "Generated with Claude Code" if Claude Code did not make the change. The label is only worth something when it is honest.

## 3. Watch CI run

```bash
gh pr checks --watch
```

Wait until `checks` finishes. The third check below needs one pull request run that ended with `success`. If your `checks` job fails, read the log with `gh run view --log-failed`, fix the cause, and push another commit to the same branch.

## 4. Review it like an agent's pull request

Use the five checks from the lesson. Replace `N` with your pull request number, which `gh pr list` shows:

```bash
gh pr view N --json additions,deletions,changedFiles
gh pr view N --json files --jq '.files[].path'
gh pr diff N
gh pr diff N | grep -n -i -E "key|token|secret|password|/Users/"
```

Answer for yourself: Is the size right for "add three lines"? Is there any file you did not ask for? Is there any key, token or personal path? Does the body explain the change? Then **leave the pull request open**. Do not merge it.

## 5. Optional: try a worktree

In your repo folder:

```bash
git worktree add -b claude/second-try ../practice-second-try
git worktree list
git switch claude/second-try
git worktree remove ../practice-second-try
git branch -d claude/second-try
```

The list shows two folders on two branches. The `git switch` runs in your main folder while the second worktree still holds `claude/second-try`. Read the error: git says the branch is already used by the other worktree.

## Check my work

Set `PRACTICE_REPO` in `.env`, then press **Check my work**. It runs three read-only `gh` calls:

- At least one pull request (open, closed or merged) comes from a branch whose name starts with `claude/`.
- At least one such pull request has the words "Claude Code" in its body.
- At least one workflow run on a pull request in the repo finished with `success`.

The checks read only the 100 newest pull requests and the 50 newest pull request runs. The check cannot tell whether Claude Code really made the change. It reads text, so the honesty is yours.
