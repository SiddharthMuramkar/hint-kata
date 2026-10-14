# Task: review and fix your own pull request

You will open a draft pull request in your practice repo, leave a review comment that contains a `suggestion` block, apply it with one click, resolve the thread, and mark the pull request ready for review. As the author you cannot approve your own PR, so you will submit the review with the **Comment** decision. That is all GitHub offers you on your own work, and it is enough to practise the whole loop.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. It is a public repo with a ruleset on `main`. If you do not have one yet, stop here and do the setup in lesson GH1 first. The checker below needs it.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code.

## 1. Open the repo and make a branch

1. In VS Code, choose **File > Open Folder** and open your practice repo folder.
2. Open the terminal with **View > Terminal**.
3. Run:

```bash
git switch main
git pull
git switch -c review-practice
```

## 2. Add a file with a small mistake, and open a draft PR

1. In the **Explorer**, create a new file called `REVIEW.md`.
2. Paste these three lines. The mistake in line 2 is on purpose:

```markdown
# Review notes
Reviews catch mistaks before they reach main.
A small pull request is easier to review.
```

3. Save the file, then commit it, push it and open the PR **as a draft**:

```bash
git add REVIEW.md
git commit -m "Add review notes"
git push -u origin review-practice
gh pr create --draft --fill
```

`gh pr create` prints the address of the PR. A draft says "not ready yet", which is exactly what you want while you review your own work.

## 3. Read your own diff

```bash
gh pr diff
```

Now open the PR in the browser with `gh pr view --web` and click the **Files changed** tab. This is the view a reviewer uses. Read the diff as if someone else wrote it.

## 4. Leave a comment with a suggestion block

1. On **Files changed**, hover over line 2 of `REVIEW.md` and click the blue comment icon.
2. In the comment box, click the **suggestion** icon (a small diff symbol). GitHub fills the box with the line, inside a fenced block that starts with three backticks and the word `suggestion`.
3. Fix the typo inside the block, so it says `Reviews catch mistakes before they reach main.` Add a short sentence above the block, for example "Typo in this word."
4. Click **Start a review**. The comment is now pending, which means only you can see it.
5. Click **Review changes** at the top of the page. Leave the summary short, choose **Comment** (the only option that is open to the author of the PR) and click **Submit review**.

Your comment must be **submitted**. A pending comment does not count.

## 5. Apply the suggestion

1. On the PR page, find your comment. It shows the change as a diff and has a **Commit suggestion** button.
2. Click **Commit suggestion**. In the commit message box, replace the default text with:

```text
Apply suggestion from code review
```

3. Click **Commit changes**.

The word "suggestion" in the message matters: the checker looks for it. GitHub's own default message for one suggestion does not always contain it.

The commit is on GitHub now, not on your laptop. Bring it down:

```bash
git pull
git log --oneline -3
```

You should see your new commit at the top, and `REVIEW.md` should have the fixed word.

## 6. Resolve the thread and mark the PR ready

1. In the conversation, find your comment thread and click **Resolve conversation**. The thread collapses.
2. Mark the PR as ready for review, with the **Ready for review** button at the bottom of the PR page, or with:

```bash
gh pr ready
```

Check the result with `gh pr view --json isDraft,reviewDecision`. `isDraft` should now be `false`.

## 7. Optional

- If a friend has access to your practice repo, ask them to review it. Request them with `gh pr edit --add-reviewer <login>`, and run the same command again to re-request a review after you make changes.
- You can merge now with `gh pr merge --squash --delete-branch`, or leave the PR open. The checks below do not need a merge.

## Check my work

Set `PRACTICE_REPO` in `.env`, then press **Check my work**. It runs read-only `gh` calls on your public repo and looks for these four things:

- A submitted review comment whose text contains a `suggestion` block. It looks at the newest 100 review comments.
- A commit on one of your newest 30 PRs whose first line contains the word "suggestion". This is the commit you made with **Commit suggestion**.
- At least one review thread marked as resolved, on one of your newest 50 PRs.
- At least one PR with a "ready for review" event in its history, on one of your newest 50 PRs. A PR that you opened as a normal PR (not as a draft) never gets this event, so open it with `--draft`.

The checker cannot tell who wrote the comment or which PR the pieces came from, so it only shows that the loop happened somewhere in your repo. If a line shows 0 right after you finish a step, wait a minute and press the button again, because GitHub's search can lag a little.
