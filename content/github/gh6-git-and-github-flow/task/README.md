# Task: a branch, two commits, a push and an open pull request

You will run the first half of GitHub flow in your practice repo. You make a branch called `feature/greeting`, make two commits that each change `greeting.txt`, push the branch with `-u`, and open a pull request. You do **not** merge it. The checker looks at the open pull request.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. It must be a public repo. If you do not have one yet, stop here and do the setup in lesson GH1 first.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code.

If you did lesson GH4, your repo already has a `greeting.txt` file. If not, it does not, and the first commit below creates it. Both cases work with the commands here, because they add a line to the end of the file.

## 1. Start from an up-to-date main and make the branch

1. In VS Code, choose **File > Open Folder** and open your practice repo folder.
2. Open the terminal with **View > Terminal**.
3. Run:

```bash
git switch main
git pull
git switch -c feature/greeting
git branch -vv
```

`git branch -vv` lists your branches. `feature/greeting` has a commit id and a message, but nothing in square brackets. It has no upstream yet.

## 2. Make two commits

Each commit changes `greeting.txt`. Each message has a short subject and a body that says why. Every `-m` makes one paragraph.

First commit:

```bash
echo "Hello from feature/greeting" >> greeting.txt
git add greeting.txt
git commit -m "Add a greeting line" -m "The practice file now says hello. This is the first of two small commits."
```

Second commit:

```bash
echo "Goodbye from feature/greeting" >> greeting.txt
git add greeting.txt
git commit -m "Add a goodbye line" -m "A second small commit, so the history of the branch has two steps."
```

Now look at what you made:

```bash
git log --oneline --graph
git rev-parse main feature/greeting
```

The log shows two new commits on top of the commit where `main` is. `git rev-parse` prints two different ids, because only `feature/greeting` moved. Run `git cat-file -p HEAD` too, and find the `parent` line.

Make exactly two commits. The checker counts them.

## 3. Push the branch with -u

This is its own command:

```bash
git push -u origin feature/greeting
```

Git says `branch 'feature/greeting' set up to track 'origin/feature/greeting'`. Now look again:

```bash
git branch -vv
git branch -r
git status
```

`git branch -vv` shows `[origin/feature/greeting]` next to your branch. `git branch -r` lists the bookmark `origin/feature/greeting`. `git status` says your branch is up to date with it.

## 4. Open the pull request, and do not merge it

```bash
gh pr create --title "Add greeting lines" --body "Two small commits that add a hello line and a goodbye line to greeting.txt. Practice for lesson GH6."
```

`gh pr create` prints the address of the PR. Open it with `gh pr view --web`. Look at the **Commits** tab, which lists your two commits, and at **Files changed**.

Leave the pull request open. Do not merge it, and do not delete the branch yet. Your ruleset may ask for the `checks` status. You do not have to wait for it, because you are not merging.

## Check my work

Set `PRACTICE_REPO` in `.env`, then press **Check my work**. It runs four read-only `gh` calls on your public repo, and shows what each one returned:

1. **The branch exists.** `feature/greeting` must exist on GitHub. The call returns its name, and the name must be exactly `feature/greeting`.
2. **The branch history has 3 to 10 commits.** The call asks GitHub for the newest 10 commits on the branch and counts them. The count includes your two commits **and the commits that were already there**, at least the first commit of the repo. A repo whose `main` has one commit gives 3. A repo with a long history gives 10, because 10 is the most the call returns. Any number from 3 to 10 passes. A 1 or a 2 means your commits are not on GitHub yet.
3. **Exactly one open pull request comes from `feature/greeting`.** The count must be exactly 1. A 0 means you have no open PR from that branch. A 2 means there are two.
4. **That pull request holds exactly 2 commits.** This counts only the commits in the PR, so the base commit is not in it. The number must be exactly 2.

If check 4 shows 3 or more, you made an extra commit. You cannot remove it here, because force pushes are not part of this flow. Close the PR and the branch, and do steps 1 to 4 again:

```bash
git switch main
gh pr close feature/greeting --delete-branch
git branch
```

`gh pr close --delete-branch` removes the branch on GitHub and in your clone. If `git branch` still lists `feature/greeting`, remove it with `git branch -D feature/greeting`. (`-D` is needed here because the branch was never merged.)

If a number is wrong right after you finish a step, wait a few seconds and press the button again.

## 5. Optional: finish the loop

Press **Check my work** first, because the checks need an open pull request. Then you can finish the loop. Do not press the button again after the merge: the site uses your most recent result, and a check run after the merge would fail.

```bash
gh pr merge --squash --delete-branch
git switch main
git pull
git fetch --prune
git log --oneline --graph -3
git branch -vv
```

The log shows one new commit for the whole branch, because of the squash. If your ruleset requires the `checks` status from lesson GH2, run `gh pr checks --watch` before the merge and wait for it to pass. After the merge, `feature/greeting` is gone from GitHub and from your clone, and `git branch -vv` shows only your other branches.