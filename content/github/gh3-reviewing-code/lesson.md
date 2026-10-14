---
id: gh3-reviewing-code
track: github
title: "Reviewing code well"
minutes: 25
pins:
  gh: "2.102"
sources:
  - github-pull-requests-concepts-giving-reviews
  - github-pull-requests-concepts-helping-others-review-your-changes
  - github-pull-requests-how-tos-review-pull-requests-reviewing-proposed-changes-in-a-pull-request
  - github-pull-requests-how-tos-review-pull-requests-incorporating-feedback-in-your-pull-request
  - github-pull-requests-how-tos-create-pull-requests-requesting-a-pull-request-review
---
A pull request is a request for a second pair of eyes. In lesson GH1 you learned the signals that make a PR ready to merge. This lesson is about the human part of those signals: how to ask for a good review, how to give one, and how to act on one. You finish by running a small review on your own practice repo. This site is not affiliated with GitHub. It teaches how GitHub works and links to the official pages.

## What a review is for

Tests answer a narrow question: "does the code do what the tests expect?" A review answers wider ones. Is this the right change? Will the next person understand it? Did it touch something that nobody mentioned? A green check cannot tell you that a function name is misleading or that a secret slipped into a config file.

GitHub names two benefits. A review helps **catch issues early**, while they are cheap to fix. It also **shares knowledge**: the reviewer learns what changed, and the author learns how someone else reads the code. See [Giving reviews](https://docs.github.com/en/pull-requests/concepts/giving-reviews).

Anyone with read access to the repository can review and comment. The review conversation lives in the PR timeline, so the whole team can follow it and see why a decision was made.

A review is not a test of the author. It is a way to make the change better before it becomes part of the shared project. Keep that in mind when you write comments in the sections below.

## Making your PR easy to review

Review quality starts with the author. A reviewer who is tired, confused or looking at 2,000 changed lines will skim. See [Helping others review your changes](https://docs.github.com/en/pull-requests/concepts/helping-others-review-your-changes).

- **Keep it small.** One PR should serve one purpose. Small PRs are easier to understand, quicker to review and safer to merge. If a change grows, split it. A refactor, a new feature and a dependency bump belong in three PRs.
- **Explain it.** A clear title and a short description say what the problem was, what you did and where the reviewer should look first. If the change touches many files or needs a reading order, say so. Link the issue it closes.
- **Review your own PR first.** Open the diff and read it as if someone else wrote it. You will find stray debug lines, accidental files and forgotten tests. You also show the reviewer that the PR is ready for their time.
- **Flag risk.** If the PR touches dependencies, permissions, workflows or code that handles secrets, say it in the description. Those are the changes where a second look matters most.
- **Show the status.** Labels and the draft state tell people whether to look now or later.

### Draft, then ready

A **draft** PR says: "I want early feedback, but this is not ready." Reviewers can comment, but nobody should expect a final review. When you are done, mark it **ready for review**. From the terminal:

```bash
gh pr create --draft --fill      # open it as a draft
gh pr ready                      # later: mark it ready for review
```

### Asking a person for a review

To request a review you need write access to the repository. The person or team you ask needs at least read access, and they get a notification. In the PR sidebar, open **Reviewers** and pick a name. GitHub suggests people based on who changed those lines before. Be careful with big teams: asking a whole team can notify every member. See [Requesting a pull request review](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/requesting-a-pull-request-review).

The terminal can do it too: `gh pr edit --add-reviewer <login>`. The same flag asks again, which you need after you make changes.

## Reading a diff well

Do not read a diff from the top like a story. Read it with a plan. See [Reviewing proposed changes in a pull request](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/reviewing-proposed-changes-in-a-pull-request).

1. **Start with the why.** Read the title, the description and the linked issue. You cannot judge a change if you do not know its goal. Then check that the diff matches that goal.
2. **Open the Files changed tab.** The tab shows the whole proposed change. Use the file tree or the filter to jump to a file. You can switch between a unified and a split view, and hide whitespace-only changes.
3. **Go one file at a time.** After you finish a file, tick **Viewed**. The file collapses, and the progress bar at the top of the PR shows how much you have covered. If the author changes that file later, GitHub removes your tick, so you know to look again.
4. **Read the risky files first.** Deleted tests, workflow files, dependency lists and anything near secrets deserve more attention than a renamed variable.

### Commits or the whole diff?

The **Commits** tab shows how the branch changed over time. The **Files changed** tab shows the net result against the base branch. They answer different questions.

- Use the **whole diff** to judge the final change. This is what will land on `main`.
- Use **one commit at a time** when the author tells a story in steps (for example, "move code" and then "change behaviour"), or when new commits arrived after your last look and you only want to see what is new.

If the branch has many small fix-up commits, the whole diff is almost always the better view. The commits are noise, and this repo squashes them anyway.

From the terminal you can read the same diff with `gh pr diff <number>`, and list the changed files with `gh pr view <number> --json files`.

## Comments, suggestions and decisions

A review is made of line comments and one final decision. See [Giving reviews](https://docs.github.com/en/pull-requests/concepts/giving-reviews).

### One comment or a whole review?

On the Files changed tab, hover over a line and click the blue comment icon. To comment on several lines, drag across the line numbers or hold Shift and click the last one. Then you have two choices:

- **Add single comment** posts it now. The author is notified at once.
- **Start a review** keeps the comment *pending*. Only you can see it, and you can edit or delete it. Add more comments the same way, then click **Review changes** and submit them together with one summary.

A review is kinder to the author. They get one complete message, not a stream of loose thoughts.

### What a useful comment looks like

Good comments are specific, give the reason and say what you want. Compare:

- Weak: "This is confusing."
- Useful: "`n` means retries here but users two lines up. Could we name it `max_retries`?"

Say whether the comment is a question, a preference or a blocker. Point at the line, not at the person. If something is good, say so. A review that only lists faults teaches the author to dread reviews.

### Suggestions: a comment the author can apply

When your fix is a few lines, show it instead of describing it. Click the suggestion icon in the comment box (a small diff symbol). GitHub copies the selected lines into a fenced block whose language tag is `suggestion`. You edit the text inside the block:

````text
This word is misspelled.

```suggestion
Reviews catch mistakes before they reach main.
```
````

The author sees your change as a diff with a **Commit suggestion** button. One click applies it as a commit on the PR branch. The `suggestion` tag is the keyword that makes this work. A plain code block would only be a picture of code that nobody can click.

### The three decisions

When you submit a review, you choose a decision. These are the same three you met in lesson GH1.

| Decision | Meaning |
| --- | --- |
| Comment | General feedback. It does not approve and it does not block. |
| Approve | "This is ready to merge." |
| Request changes | "Please fix this before the PR merges." |

Two facts matter here. First, **Request changes** is only a signal, unless the repository requires a pull request through a ruleset or branch protection. Then it can hold up the merge until the same reviewer approves. Second, **an author cannot approve their own PR**. On a PR you wrote, you can only submit **Comment**. That is why a solo developer can still leave review comments and suggestions on their own work. It is a way to read your own diff slowly and leave yourself notes. It does not give you a second opinion.

The `gh` command line can leave a whole-PR review, such as `gh pr review --comment --body "..."`. It cannot attach a comment to one line or write a suggestion block. For that you use the browser.

## Responding to feedback

You have a review. Now what? See [Incorporating feedback in your pull request](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/incorporating-feedback-in-your-pull-request).

1. **Read all of it before you change anything.** Some comments depend on each other.
2. **Apply the suggestions you agree with.** If you have write access, click **Commit suggestion**. GitHub makes one commit on the PR branch, and you type a short, meaningful commit message for it. The person who suggested the change is named as a co-author. To fold several suggestions into one commit, click **Add suggestion to batch** on each, then **Commit suggestions** once.
3. **Answer what you do not apply.** If you disagree, say why. A reviewer cannot know that you chose not to change something unless you write it. If the idea is good but too big for this PR, open an issue to track it and link the issue in your reply.
4. **Resolve threads.** When a comment is dealt with, mark its conversation as **Resolved**, so that the PR shows what is still open. See [Resolving reviews](https://docs.github.com/en/pull-requests/concepts/resolving-reviews). Some repositories require every thread to be resolved before the merge, so an open thread is an open question.
5. **Re-request a review.** After substantial changes, ask the reviewer to look again. In the **Reviewers** sidebar, click the sync icon next to their name, or run `gh pr edit --add-reviewer <login>`.

If a repository requires approvals and also dismisses stale ones, pushing a new commit to an approved PR removes the approval. You need a new one before you merge.

## How this site's own PRs were reviewed

This site has no second human, so each change is read by an agent as well as checked by CI. A subagent called `diff-reviewer` reads a PR diff and returns a list of findings (correctness, tests, scope creep, secrets, attribution). It is described in [docs/HARNESS.md](https://github.com/siddharth-0044/hint-kata/blob/main/docs/HARNESS.md). It is a useful reader, but its findings are input to a decision, not an approval. A person still decides what to apply. The habits in this lesson (small diffs, clear descriptions, specific comments) work just as well when the reviewer is a machine.

Now try the whole loop on your own practice repo: open a PR as a draft, leave a comment with a `suggestion` block, apply it, resolve the thread and mark the PR ready. The task page lists each step and says what **Check my work** looks for.

**Sources:**
[Giving reviews](https://docs.github.com/en/pull-requests/concepts/giving-reviews),
[Helping others review your changes](https://docs.github.com/en/pull-requests/concepts/helping-others-review-your-changes),
[Reviewing proposed changes in a pull request](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/reviewing-proposed-changes-in-a-pull-request),
[Incorporating feedback in your pull request](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/incorporating-feedback-in-your-pull-request),
[Requesting a pull request review](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/requesting-a-pull-request-review).
Adapted from GitHub Docs, © GitHub, CC BY 4.0. Modified: summarized and adapted. Checked with `gh` 2.102.
