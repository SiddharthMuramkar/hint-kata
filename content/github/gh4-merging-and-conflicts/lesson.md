---
id: gh4-merging-and-conflicts
track: github
title: "Merging, conflicts and reverts"
minutes: 30
pins:
  gh: "2.102"
  git: "2.54"
sources:
  - github-repositories-configuring-branches-and-merges-in-your-repository-configuring-pull-request-merges-about-merge-methods-on-github
  - github-pull-requests-how-tos-merge-and-close-pull-requests-resolving-a-merge-conflict-using-the-command-line
  - github-pull-requests-how-tos-merge-and-close-pull-requests-reverting-a-pull-request
  - github-pull-requests-how-tos-merge-and-close-pull-requests-merging-a-pull-request
---
A pull request is ready, the checks are green, and you click merge. What exactly happens to your history? And what do you do when GitHub says "This branch has conflicts"? Or when a change that was already merged turns out to be a mistake? This lesson answers those three questions. At the end you do all three in your own practice repo. This site is not affiliated with GitHub. It teaches how GitHub works and links to the official pages.

## The three merge methods

When a pull request lands on `main`, GitHub can do it in three ways. Which ones you see on the button depends on what the repository allows. ([About merge methods](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github))

Say your branch `login` has three commits: A, B and C. Here is what each method leaves on `main`:

```text
Merge commit        Squash and merge      Rebase and merge
------------        ----------------      ----------------
M  (merge commit)   S  (A+B+C in one)     C'
|\                                        B'
| C                 one new commit        A'
| B                 in a straight line
| A                                       three new commits,
|/                                        no merge commit
```

- **Merge commit** (the default button). All your commits come over unchanged, and GitHub adds one extra commit, the merge commit, that has two parents. Nothing is lost, but history becomes a web of branches and merges.
- **Squash and merge.** The three commits are squashed into one new commit that holds the sum of their changes. `main` gets a single ordinary commit, in a straight line. The PR title becomes the commit message by default.
- **Rebase and merge.** The commits are replayed one by one on top of `main`. There is no merge commit, so history stays a straight line. But the copies are new commits: they get new SHAs, and GitHub sets itself as the committer. The originals on your branch are not the commits that landed.

**Why this repo squashes.** Work-in-progress commits such as "fix typo" or "try again" are useful while you work and noise afterwards. With squash, one PR becomes one commit with one clear title. The log reads like a list of finished changes. It also makes undoing a change easy, as you will see in the revert section. The price is real, though. You lose the individual commits and the record of who made each one, and the original SHAs are gone, which makes some git commands harder to use.

**Require linear history.** A ruleset can include a rule called "Require linear history". It forbids merge commits on the branch, so every change must be a straight line. Which button fails? **Merge commit**, because it is the only method that creates a merge commit. Squash and rebase both still work. (A merge commit *inside* your PR branch, like the one you will make when you fix a conflict, is fine for a squash merge. The squash folds it into the single new commit, and the rule only looks at what lands on `main`.)

If you use a merge queue, the queue chooses the method for you. And if the repository allows only one method, that is the only button you see.

## What a conflict is

Git merges by comparing three versions of each file: the common ancestor (where the two branches split), your version, and their version. For each line, git asks "who changed it?"

- Only one side changed the line: take that change. No problem.
- Both sides changed *different* lines: take both. No problem.
- Both sides changed the *same* lines in different ways: **conflict**. Git cannot know which version is right, or whether the answer is a mix of both. It stops and asks a human.

The same happens when one branch deletes a file and the other edits it. ([Resolving a merge conflict using the command line](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/resolving-a-merge-conflict-using-the-command-line))

Git decides only by looking at text. It does not know what your code means. So two things follow:

- A conflict is not an error or a sign that you did something wrong. It is git being honest that it needs a decision.
- The absence of a conflict is not proof that the code works. Two branches can merge cleanly and still break each other, for example when one renames a function and the other adds a call to the old name. That is what the tests in CI are for.

You see a conflict on GitHub as a message on the PR: "This branch has conflicts that must be resolved", and the merge button is disabled. From the terminal, `gh pr view <number> --json mergeable,mergeStateStatus` shows `CONFLICTING` and `DIRTY`. It can say `UNKNOWN` for a few seconds while GitHub calculates, so ask again. Also remember from lesson GH2: a workflow that triggers on `pull_request` does not start while the PR has a conflict.

## Resolving a conflict on the command line

You fix a conflict on your branch, not on `main`. You bring `main` into your branch, settle the conflicting lines, and push. Then the PR merges cleanly. The terminal inside VS Code is all you need (View > Terminal).

```bash
git switch my-branch
git fetch origin
git merge origin/main
```

Git replies with something like `CONFLICT (content): Merge conflict in greeting.txt` and `Automatic merge failed`. You are now in the middle of a merge. Run `git status` and look for the section **Unmerged paths** with `both modified:` next to each file. If you panic at any point, `git merge --abort` puts your branch back exactly as it was.

Open the file. Git has written both versions into it:

```text
Welcome to the project.
<<<<<<< HEAD
Hello from my branch
=======
Hello from main
>>>>>>> origin/main
Bye.
```

Read the markers like this. Everything from `<<<<<<< HEAD` to `=======` is *your* branch, the one you are standing on. Everything from `=======` to `>>>>>>> origin/main` is what came in from `main`. The three marker lines are not part of your file. They are notes from git, and you must delete all three.

Now decide. Keep yours, keep theirs, or write a new line that combines both. Edit the file until it reads the way it should, with no markers at all.

```text
Welcome to the project.
Hello from my branch and from main
Bye.
```

VS Code shows small buttons above each conflict (Accept Current, Accept Incoming, Accept Both, Compare) and a **Resolve in Merge Editor** button that opens a three-pane view. They are a convenient way to edit the file, and nothing more: behind them it is the same text with the same markers. This lesson shows the terminal way, because it is the same everywhere and it makes you see what git did. Whichever way you edit, you must check the result yourself.

Finish the merge:

```bash
git diff --check        # warns about leftover conflict markers
git add greeting.txt    # tells git "I resolved this file"
git commit              # a merge message is already filled in; save and close
git push
```

Do not skip the check. Git does not read your file when you run `git add`. It trusts that you are done. If you leave one `=======` line behind, the commit works and the stray line is now part of your project. Open the file once more, or run `git diff --check`, before you stage it.

When you push, the PR updates by itself, the conflict message disappears, and the checks run again on the combined code. (If one branch *deleted* the file, the choice is `git add <file>` to keep it or `git rm <file>` to delete it, then commit.)

## Keeping branches short-lived

Conflicts grow with time. The longer your branch lives, the more `main` moves under it, and the more likely someone has touched the same lines. A branch that lives a few hours rarely conflicts. A branch that lives a month almost always does. Some habits that keep conflicts rare:

- **Make small pull requests.** One change, one PR. A small diff has fewer lines that can collide, and it is easier to review.
- **Start from a fresh `main`.** Run `git switch main`, `git pull`, then `git switch -c new-branch`.
- **Bring `main` in often.** On a branch that lives more than a day, run `git fetch origin` and `git merge origin/main` now and then. Small conflicts are quick to fix. On GitHub, `gh pr update-branch` does the same merge for you when there is no conflict.
- **Keep unrelated changes apart.** Do not reformat a whole file inside a feature PR. A formatting change touches many lines, and every other branch that touches the file will collide with it.
- **Delete the branch after you merge it, and never reuse it.** This one matters most for squash. Squashing writes a *new* commit on `main`. Git does not know that your old commits and that new commit are the same work. If you keep committing on the old branch and open another PR, the new PR lists the old commits again, and you may have to resolve the same conflicts again. Delete the branch and start the next change from `main`.

## Reverting a merged pull request

Sometimes a change that is already merged turns out to be wrong. You cannot quietly delete it from `main`. Other people have already pulled it, and a ruleset normally blocks rewriting history. The safe answer is a **revert**: a new commit that does the exact opposite of the old one. History is never rewritten. It just gets one more entry that says "we undid this". ([Reverting a pull request](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/reverting-a-pull-request))

On GitHub it is two steps:

1. Open the merged PR and click **Revert** near the bottom. GitHub creates a new branch and a new PR whose title starts with `Revert`.
2. Merge that PR like any other. It goes through your normal rules and checks.

You need write access. If the button is missing, the PR is not merged yet or you lack the permission.

This is where squash pays off. A squash-merged PR is **one commit**, so its revert is also **one commit**, and one click undoes the whole feature. With the other methods it is harder:

- A **merge-commit** PR is a merge commit with two parents. Git needs to know which parent to go back to: `git revert -m 1 <merge-sha>` (parent 1 is the `main` side).
- A **rebase-merged** PR is several separate commits, and you have to revert each one.

From the terminal you can revert one commit with `git revert <sha>`, then push it on a branch and open a PR. The GitHub page notes you may need this if reverting the whole PR gives conflicts, or if the PR was not merged on GitHub. `gh pr revert <number>` does the button's job from the CLI.

One trap: after a revert, the original change is on `main` *and* so is its undo. If you later want the change back, merging the old branch again does nothing, because git thinks that work is already in. Revert the revert, or open a new PR with a fixed version.

## Merging from the terminal

You can do all of the above without leaving VS Code. ([Merging a pull request](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request))

```bash
gh pr checks --watch                      # wait until the checks finish
gh pr merge --squash --delete-branch      # squash, then delete the branch
git switch main
git pull
```

The flags `--squash`, `--merge` and `--rebase` pick the method. Leave them out and `gh` asks you. A method the repository does not allow will be refused. `--delete-branch` removes the remote branch and your local one, which is the "never reuse a branch" habit in one flag. You can set the commit message with `--subject` and `--body`.

**Auto-merge.** If the checks are still running, you do not have to wait. Run:

```bash
gh pr merge --squash --delete-branch --auto
```

`--auto` tells GitHub: merge this PR as soon as every requirement is met, for example when the required checks pass and the review rules are satisfied. The repository must have auto-merge turned on in its settings. Change your mind with `gh pr merge --disable-auto`. A good fit is a small PR with slow checks: you start the merge and move on. A bad fit is a PR you still want to read again.

A draft PR cannot be merged, and neither can one with a conflict. If `gh pr merge` refuses, run `gh pr view --json isDraft,mergeable,mergeStateStatus` first. It tells you why.

**Sources.** GitHub Docs, all adapted and summarized, CC BY 4.0, read 2026-10-14. This site is not affiliated with GitHub. Checked with `gh` 2.102 and git 2.54.
[About merge methods on GitHub](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github) ·
[Resolving a merge conflict using the command line](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/resolving-a-merge-conflict-using-the-command-line) ·
[Reverting a pull request](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/reverting-a-pull-request) ·
[Merging a pull request](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request).
Content licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
