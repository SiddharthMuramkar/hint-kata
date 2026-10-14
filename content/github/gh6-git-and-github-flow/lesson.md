---
id: gh6-git-and-github-flow
track: github
title: "Git and GitHub flow: branches, commits, remotes"
minutes: 25
pins:
  gh: "2.102"
  git: "2.54"
sources:
  - github-get-started-using-github-github-flow
  - github-pull-requests-reference-branches
  - github-pull-requests-how-tos-commit-changes-managing-branches-within-your-repository
  - github-get-started-git-basics-about-remote-repositories
---
You have used branches and pull requests since lesson GH1. This lesson looks under the hood. What is a commit? What is a branch? What do `origin` and `git push -u` mean? Why do good teams delete a branch as soon as it is merged? Once you know the answers, git stops being a list of spells and becomes a few simple ideas. At the end you run the whole loop in your own practice repo: a branch, two commits, a push and an open pull request. This site is not affiliated with GitHub. It teaches how GitHub works and links to the official pages.

Run the commands in the terminal inside VS Code (View > Terminal).

## A commit is a snapshot with a parent

A commit is one saved state of your project. It holds four things:

- a **snapshot** of every file in the project at that moment,
- the **author** and the time,
- the **message** you wrote,
- the id of its **parent**, the commit that came right before it.

You choose what goes into the next snapshot with `git add`. Then `git commit` saves it. To see a commit the way git stores it, run `git cat-file -p HEAD`. (`HEAD` means "the commit I am on now".) You get something like this:

```text
tree 80f25b6d8b775142cdd03d08ba821a5846f273b2
parent e0b7e05db62ec4d0e4367f8314a34fa237feb422
author You <you@example.com> 1791991672 +0530
committer You <you@example.com> 1791991672 +0530

Greet the whole world

A bare Hello felt unfinished. The file now greets the world.
```

The `tree` line is the snapshot. The `parent` line is the link back to the previous commit. Git builds history by following these links. The very first commit of a repo has no parent. A merge commit (lesson GH4) has two.

Three things follow:

- **A commit is a snapshot, not a diff.** Git keeps the whole state. Files that did not change are shared with the commit before, so this is cheap. The red and green lines you see on GitHub are worked out by comparing a commit with its parent.
- **A commit never changes.** Its id is a long hash, a SHA, calculated from everything above. Change one letter and the id is different. So "editing" a commit really means making a new one and leaving the old one behind. This is why squash and rebase in GH4 gave you new SHAs.
- **History is a chain.** `git log` starts at the newest commit and walks back through the parents.

`git log --oneline --graph` draws the chain, one line per commit:

```text
* a6cc6df (HEAD -> feature/greeting) Greet the whole world
* e0b7e05 Add greeting file
* a1fbaa0 (origin/main, main) Add readme
```

`--oneline` prints a short id and the first line of the message. `--graph` draws lines on the left, which starts to matter when history forks and joins. In a terminal git adds the branch names in brackets for you. Add `--all` to see every branch, not only the one you are on. ([git log manual](https://git-scm.com/docs/git-log))

## A branch is a movable pointer

A branch is a name that points at one commit. That commit is the **tip** of the branch. A branch is not a copy of your files. It is only a label.

When you make a commit, git does two things. It creates the new commit, with the old tip as its parent. Then it moves the branch name forward to the new commit. Only the branch you are on moves. `HEAD` is how git remembers which branch that is. The VS Code status bar at the bottom left shows its name.

Try it:

```bash
git switch -c feature/greeting
git rev-parse main feature/greeting
```

`git switch -c` creates a new name at the commit you are on, and moves you onto it. `git rev-parse` prints the commit that each name points at. Both lines show the same id, because a new branch starts at the same commit. It costs almost nothing, because nothing is copied. Now make two commits. Only `feature/greeting` moves:

```text
   main                      feature/greeting (HEAD)
     |                                |
     v                                v
  a1fbaa0  <---  e0b7e05  <---  a6cc6df
```

The arrows point from a commit to its parent.

**`main` and feature branches.** `main` is a branch like any other. GitHub gives the first branch of a new repo that name by default. This default branch is what visitors see when they open your repo, and it is the base for new pull requests, the branch a PR asks to merge into. Git itself gives `main` no special powers. Rules do that, such as the ruleset you made in GH1.

A branch you create for one piece of work is a **feature branch**, also called a topic branch. You always create it from an existing branch, usually `main`. On it you work in isolation from what other people do on `main`. You need write access to the repo to create a branch in it. ([Branches](https://docs.github.com/en/pull-requests/reference/branches), [Managing branches within your repository](https://docs.github.com/en/pull-requests/how-tos/commit-changes/managing-branches-within-your-repository))

Give the branch a short name that tells others what you are doing, such as `add-code-of-conduct` or `increase-test-timeout`. Slashes are fine: `feature/greeting`. This repo uses `issue-<n>-<slug>`.

## Switch and restore, not checkout

For years one command, `git checkout`, did two unrelated jobs. It moved you to another branch, and it threw away edits to a file. Git now has one command for each job. ([git checkout manual](https://git-scm.com/docs/git-checkout))

| You want to | The older way | The newer way |
|---|---|---|
| Move to a branch | `git checkout my-branch` | `git switch my-branch` |
| Make a branch and move to it | `git checkout -b my-branch` | `git switch -c my-branch` |
| Throw away uncommitted edits to a file | `git checkout -- greeting.txt` | `git restore greeting.txt` |
| Take a file out of the next commit, keep the edits | `git reset HEAD greeting.txt` | `git restore --staged greeting.txt` |

- `git switch` changes `HEAD` and updates the files in your folder to match the new branch. It stops with an error rather than lose edits you have not committed. Use `git switch -` to jump back to the branch you came from. If you give it a file name by mistake, it refuses (`fatal: invalid reference`).
- `git restore <file>` puts the saved version of the file back in your folder. Git never saved your edits, so it cannot give them back. Run it only when you mean it.
- `git restore --staged <file>` only un-stages the file. The edits stay in your folder.

The old commands still work, and you will meet them in older tutorials. Prefer `switch` and `restore` in your own work. Each does one thing, so a mistake is easier to see.

## The GitHub flow loop

GitHub flow is a light way of working, built on branches. It has seven steps, and every one of them can be done in the browser, with `gh`, or in GitHub Desktop. ([GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow))

```text
branch -> commit -> push -> pull request -> review -> merge -> delete the branch
            ^                                  |
            +------ more commits, push again --+
```

```bash
git switch main
git pull
git switch -c feature/greeting
# edit greeting.txt, then:
git add greeting.txt
git commit -m "Add a greeting line"
git push -u origin feature/greeting
gh pr create
```

1. **Branch.** Start from an up-to-date `main`. The branch is a safe place to work. Nothing reaches `main` until you merge, and others get a chance to look first.
2. **Commit.** Aim for small commits that each hold one complete change. Say you rename a variable and add tests. Put the rename in one commit and the tests in another. Later you can undo the rename and keep the tests. If both were in one commit, that would take more work.
3. **Push.** This sends your branch to GitHub. It backs up your work, lets you open it from another computer, and lets others see it.
4. **Open a pull request.** A PR asks people to look at your branch. It compares your branch (the *head*) with the branch you want to merge into (the *base*). The **Files changed** tab shows what would change if it merged. Write what you changed and what problem it solves. If it fixes an issue, put `Closes #12` in the body, and the issue closes itself when the PR merges. A **draft** PR means "not done, but have a look".
5. **Review.** Reviewers comment on the whole PR or on single lines. You answer with more commits on the same branch and push them. The PR updates by itself, and any checks run again. Lesson GH3 covered reviewing.
6. **Merge.** When the PR is approved, merge it. Branch protection can block the merge until the rules are met. GitHub keeps the comments and commits of the PR, so later readers can see why the change was made.
7. **Delete the branch.** The work is done, and a deleted branch cannot be used by accident. Nothing is lost: the PR and its commits stay, and a deleted branch can be restored.

Steps 1 to 3 happen on your computer. Steps 4 to 7 mostly happen on GitHub, and `gh` lets you do them from the terminal. Use one branch for each set of unrelated changes. Then a delay in one change does not hold up the others.

## Remotes and tracking branches

A **remote** is a name for another copy of your repo, usually the one on GitHub. It is a name tied to a URL. The usual name is `origin`.

```bash
git remote -v
```

```text
origin  https://github.com/your-user/hint-kata-practice.git (fetch)
origin  https://github.com/your-user/hint-kata-practice.git (push)
```

You can push to two kinds of address: an `https://` URL, or an SSH address such as `git@github.com:user/repo.git`. If a repo has no remote yet, `git remote add origin <URL>` creates the link. ([About remote repositories](https://docs.github.com/en/get-started/git-basics/about-remote-repositories))

**Two copies.** Your clone and the copy on GitHub each have their own branches, and each has a `main`. They drift apart when someone commits to one and not the other. Git does not sync them in the background. You move commits on purpose with `fetch`, `pull` and `push`.

**Remote-tracking branches.** Inside your clone, git keeps a bookmark for every branch it saw on the remote, such as `origin/main` and `origin/feature/greeting`. `git branch -r` lists them. A bookmark remembers where that branch was the last time you talked to GitHub. You never commit to one. Only `fetch`, `pull` and `push` move it.

**Fetch and pull.**

- `git fetch` downloads new commits and moves the `origin/...` bookmarks. It does not touch your own branches or your files, so it is safe at any time. Afterwards, `git status` may say "Your branch is behind 'origin/main' by 1 commit".
- `git pull` is a fetch plus one more step: it brings the upstream branch into the branch you are on. If you only fell behind, git moves your branch forward (a fast-forward). If both sides have new commits, git 2.54 stops with `Need to specify how to reconcile divergent branches` until you choose, for example `git pull --rebase` or `git pull --no-rebase` (a merge). When in doubt, run `git fetch`, look with `git log --oneline --graph --all`, and then decide.

**Tracking.** A local branch can be linked to one remote branch, called its **upstream**. Then git knows what to compare with. `git status` can say "up to date", "ahead" or "behind". Plain `git pull` and `git push` need no arguments. `git branch -vv` shows the link in square brackets, with `ahead 1`, `behind 1`, or `gone` if the remote branch was deleted. A clone sets this up for the default branch. A branch you create yourself has no upstream, so the first plain `git push` fails:

```text
fatal: The current branch feature/greeting has no upstream branch.
To push the current branch and set the remote as upstream, use

    git push --set-upstream origin feature/greeting
```

Git tells you the fix. `-u` is the short form of `--set-upstream`:

```bash
git push -u origin feature/greeting
```

That does two things. It pushes the branch, which creates `feature/greeting` on GitHub. And it records the link. After that, plain `git push` and `git pull` work. You need `-u` once per branch. (A setting called `push.autoSetupRemote` can do it for you on the first push. This lesson uses `-u` so you can see the step.)

```text
* feature/greeting a6cc6df [origin/feature/greeting] Greet the whole world
  main             a1fbaa0 [origin/main] Add readme
```

That is `git branch -vv` after the push. ([git push manual](https://git-scm.com/docs/git-push), [git pull manual](https://git-scm.com/docs/git-pull))

## Short-lived branches

A branch should live for hours or a few days, not weeks. GitHub's advice is to merge a pull request as soon as you can, because that pushes everyone toward smaller PRs. Lesson GH4 showed the other reason: the longer a branch lives, the further `main` moves away from it, and the more conflicts you meet.

- **One branch per change.** Unrelated changes get separate branches and separate PRs.
- **Start from a fresh `main`.** Run `git switch main`, `git pull`, then `git switch -c <name>`.
- **Open the PR early.** A draft PR is a good way to ask for feedback before you are done.
- **Delete the branch after the merge.** Then nobody uses it by accident. After a squash merge, never reuse it (GH4 explains why).

Cleaning up after a merge touches three places:

1. **GitHub.** `gh pr merge --squash --delete-branch` deletes the branch for you. You can also click **Delete branch** on the PR page, or turn on the repository setting that deletes head branches after a merge. Do not delete the branch of a PR that is still open, because GitHub then closes the PR.
2. **Your bookmarks.** Your clone keeps `origin/feature/greeting` even after the branch is gone from GitHub. `git fetch --prune` removes bookmarks whose branch no longer exists on the remote.
3. **Your local branch.** `git branch -d feature/greeting` removes it. After a squash merge, git may refuse with `the branch 'feature/greeting' is not fully merged`. A squash makes a new commit, so git cannot see your commits inside `main`. If you know the PR was merged, `git branch -D feature/greeting` forces it. (`gh pr merge --delete-branch` removes the local branch as well.) In `git branch -vv`, a branch whose remote is gone is marked `gone`.

## Good commit messages

A commit message is for the person who reads `git log` or `git blame` months from now. That person is often you.

```text
Add trailing newline to greeting.txt

The checker reads the file line by line and crashes when the
last line has no newline. Every file now ends with one.
```

- **Subject line.** The text up to the first blank line is the commit's title, and git uses it everywhere: `git log --oneline`, email patches, lists on GitHub. Git's manual suggests at most about 50 characters. Many teams allow up to 72. Neither is enforced. Git's own project asks for the imperative mood, "Add trailing newline", as if you gave an order to the code, and no full stop at the end. ([git commit manual](https://git-scm.com/docs/git-commit), [Git's patch guidelines](https://git-scm.com/docs/SubmittingPatches))
- **Blank line, then a body.** The body explains **why**. The diff already shows what changed. The message has to say what problem you solved, why you chose this way, and anything that would surprise a reader. Wrap lines at about 72 characters so they read well in a terminal.
- **One complete change per commit.** Then the message has one thing to say.

On the command line, each `-m` makes a paragraph: `git commit -m "Subject" -m "Body that explains why"`. Without `-m`, git opens your editor. Git refuses an empty message (`Aborting commit due to empty commit message`).

Weak messages are `update`, `fix`, `wip` and `final2`. They tell the reader nothing the diff does not already say. A message with the whole story squeezed into one very long subject is also hard to scan. Squash merges give the PR title to the new commit on `main` (GH4), so write PR titles like commit subjects.

## How this repo does it

This repo follows GitHub flow closely, and its rules are written down in `docs/HARNESS.md` and `.claude/rules/git.md`. Here is what they say.

- **One issue, one branch, one PR.** Every task starts as an issue. Its branch is called `issue-<n>-<slug>`, for example `issue-92-lesson-gh6` for this lesson. It gets exactly one PR. Nothing is pushed straight to `main`, and nobody force-pushes.
- **`main` is locked by a ruleset.** On 2026-10-14 the ruleset on the default branch blocked deleting the branch, blocked force pushes, required a pull request with the squash method, and required the CI job `checks` to pass. It had no bypass list, so it applies to the owner too. You can read it yourself: `gh api repos/siddharth-0044/hint-kata/rulesets`.
- **Squash only.** The repo allows only squash merges and deletes the head branch after each merge. So `git log --oneline --graph` on `main` is a straight line, with one commit per PR. Each title ends with the PR number, such as `(#70)`.
- **Commit messages** start with a type such as `feat:`, `fix:`, `docs:`, `test:` or `chore(scope):`. They end with a `Co-Authored-By:` line that names the AI model that helped.
- **PR text is a small lesson.** It says what changed, why, and which file to read first. It ends with `Closes #<n>`, and a line saying it was made with Claude Code. The same text is saved as one new file in `docs/learning-log/`. Nobody edits the shared logs inside a task PR, so two PRs never conflict over them.
- **Guard rails for the AI builders.** Hooks and permission rules in `.claude/` block pushing to `main` and force pushes. Each builder works in its own git worktree, an extra folder with its own branch, so two tasks never share a branch.

Try it in your own clone of this repo:

```bash
git fetch --prune
git log --oneline --graph -8 origin/main
```

You see a straight line of finished changes, each with its PR number.

**Sources.** Adapted from GitHub Docs, © GitHub, CC BY 4.0. Modified: summarized and adapted. Read 2026-10-14. This site is not affiliated with GitHub. Checked with `gh` 2.102 and git 2.54, using the git manual pages and a scratch repo. The commit-message advice also follows the git project's own patch guidelines.
[GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow) ·
[Branches](https://docs.github.com/en/pull-requests/reference/branches) ·
[Managing branches within your repository](https://docs.github.com/en/pull-requests/how-tos/commit-changes/managing-branches-within-your-repository) ·
[About remote repositories](https://docs.github.com/en/get-started/git-basics/about-remote-repositories).
Content licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
