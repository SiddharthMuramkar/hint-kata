# Task: make a conflict, resolve it, squash-merge, then revert

You will make two branches that change the same line of a file. You merge one, see the other one turn into a conflict, fix it on the command line, squash-merge it, and then undo that merge with the **Revert** button on GitHub.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. It is a public repo with a ruleset on `main` that requires a pull request. If you do not have one yet, stop here and do the setup in lesson GH1 first. The checker below needs it.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code.

If your ruleset also requires the `checks` status check from lesson GH2, run `gh pr checks <branch> --watch` before every merge below and wait for it to pass. If your repo has no workflow, skip that.

## 1. Open the repo and add a file

1. In VS Code, choose **File > Open Folder** and open your practice repo folder.
2. Open the terminal with **View > Terminal**.
3. Make a branch with a three-line file, and merge it through a pull request:

```bash
git switch main
git pull
git switch -c add-greeting
printf 'Welcome to the project.\nHello, world\nBye.\n' > greeting.txt
git add greeting.txt
git commit -m "docs: add greeting file"
git push -u origin add-greeting
gh pr create --fill
gh pr merge --squash --delete-branch
git switch main
git pull
```

## 2. Make two branches that edit the same line

Both branches start from the same `main`, and both change line 2 of `greeting.txt`.

1. Branch A. Open `greeting.txt` in VS Code, change line 2 to `Hello from A`, and save. Then:

```bash
git switch -c greet-a
git add greeting.txt
git commit -m "docs: greet from A"
git push -u origin greet-a
gh pr create --fill
```

2. Branch B. Go back to `main` first, so that B does not include A's change:

```bash
git switch main
git switch -c greet-b
```

Open `greeting.txt`, change line 2 to `Hello from B`, and save. Then:

```bash
git add greeting.txt
git commit -m "docs: greet from B"
git push -u origin greet-b
gh pr create --fill
```

You now have two open pull requests that change the same line.

## 3. Merge A, and watch B break

1. Squash-merge A. You can run this from any branch, because you name the pull request by its branch:

```bash
gh pr merge greet-a --squash --delete-branch
```

2. Ask GitHub about B:

```bash
gh pr view greet-b --json mergeable,mergeStateStatus
```

You should see `"mergeable":"CONFLICTING"` and `"mergeStateStatus":"DIRTY"`. If it says `UNKNOWN`, wait a few seconds and run it again. Open the pull request page on GitHub and find the message "This branch has conflicts that must be resolved".

## 4. Resolve the conflict on the command line

1. Bring the new `main` into your branch:

```bash
git switch greet-b
git fetch origin
git merge origin/main
git status
```

`git merge` stops with `CONFLICT (content): Merge conflict in greeting.txt`, and `git status` lists `greeting.txt` under **Unmerged paths**.

2. Open `greeting.txt` in VS Code. You will see:

```text
Welcome to the project.
<<<<<<< HEAD
Hello from B
=======
Hello from A
>>>>>>> origin/main
Bye.
```

Replace the five marker and greeting lines with one line that keeps both greetings:

```text
Welcome to the project.
Hello from A and B
Bye.
```

Save the file. You may use the buttons VS Code shows above the conflict if you like, but check the result: no `<<<<<<<`, `=======` or `>>>>>>>` may be left.

3. Check, stage, finish the merge and push:

```bash
git diff --check
git add greeting.txt
git commit --no-edit
git push
```

`git diff --check` should print nothing. `git commit --no-edit` keeps the merge message git prepared. If you get stuck, `git merge --abort` puts the branch back as it was, and you can start step 4 again.

4. Check that the conflict is gone, wait for any required checks, and squash-merge:

```bash
gh pr view greet-b --json mergeable,mergeStateStatus
gh pr merge greet-b --squash --delete-branch
git switch main
git pull
git log --oneline -4
```

Even though your branch held two commits (yours and the merge commit), `main` got only one new commit. That is what squash does.

## 5. Revert it from the GitHub UI

1. In your browser, open your repo on GitHub, click **Pull requests**, choose **Closed**, and open the pull request for `greet-b`.
2. Near the bottom of the page, click **Revert**. GitHub makes a new pull request, with a title that starts with `Revert`.
3. Open that new pull request and merge it with **Squash and merge**. (Prefer the terminal? Run `gh pr merge <number> --squash --delete-branch`.)
4. Update your copy and look at what happened:

```bash
git switch main
git pull
git log --oneline -4
cat greeting.txt
```

The log shows a new commit that starts with `Revert`, and line 2 of `greeting.txt` is back to `Hello from A`. Nothing was deleted from history. The revert is one more commit on top.

## Check my work

Set `PRACTICE_REPO` in `.env`, then press **Check my work**. It runs read-only `gh` calls:

- At least two pull requests are merged in your repo.
- One of the last 100 commits on the default branch has a message that starts with `Revert`.
