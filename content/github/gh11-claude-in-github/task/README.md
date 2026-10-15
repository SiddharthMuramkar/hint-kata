# Task: write a safe, switched-off claude.yml in your practice repo

You will add one workflow file, `.github/workflows/claude.yml`, that would run `claude-code-action` when someone writes `@claude` in a comment. You pin the action to a full commit SHA, give the action a small token, and leave the credential out. The workflow stays switched off in practice, because you install no app and add no secret.

You work in your **practice repo**, the one in `PRACTICE_REPO` from lesson GH1. It is a public repo. If you do not have it yet, stop here and do the setup in lesson GH1 first. The checker below needs it.

The commands use bash or zsh quoting. On Windows, open a Git Bash terminal in VS Code.

**Three rules for this task.**

- **Do not install the Claude GitHub app and do not run `/install-github-app`.** That needs repo admin rights and sets up a secret. The lesson explains it. You only read about it.
- **Do not add a secret.** The file will name `ANTHROPIC_API_KEY`, but the secret does not exist in your repo. Never paste a real API key or token into a file, a pull request or chat.
- **Do not write `@claude` in any comment in your practice repo, including on the pull request in step 5.** Any comment with that text would start the job. With no secret, we expect that run to fail. We did not run it. A failed run does no harm, but it makes noise.

## 1. Open the repo and make a branch

1. In VS Code, choose **File > Open Folder** and open your practice repo folder.
2. Open the terminal with **View > Terminal**.
3. Run:

```bash
git switch main
git pull
git switch -c add-claude-workflow
```

## 2. Look up the commit SHA of the release

Your file will pin the action to a full commit SHA. Look it up yourself, with the `gh` CLI. The lesson explains why the first command shows a tag object and not a commit:

```bash
gh api repos/anthropics/claude-code-action/git/ref/tags/v1.0.249 --jq '.object'
```

Read the `type`. If it says `tag`, take the `sha` and follow it one step:

```bash
gh api repos/anthropics/claude-code-action/git/tags/12732ed86c7c48cf319dc8c528fa0b24c81c3486 --jq '.object'
```

The `type` should now say `commit`. The shortcut for the same answer is:

```bash
gh api repos/anthropics/claude-code-action/commits/v1.0.249 --jq '.sha'
```

When this lesson was written (2026-10-14), `v1.0.249` was the newest release. Its commit SHA was:

```text
34968b5981d5d170904281aa3df6f3c0d4a28855
```

If you see the same SHA, you checked it right. If a newer release exists when you do this, you may pin to that one. Use the same lookup, and use the commit SHA you find, with its own version in the comment. List releases with `gh release list -R anthropics/claude-code-action --limit 5`. Do not use `v1`: it is a moving tag.

## 3. Create the workflow file

1. In the Explorer, create the file `.github/workflows/claude.yml`. VS Code makes the folders for you when you type the whole path in the new-file box.
2. Paste this into it. If you chose a newer release in step 2, change the SHA and the `# v` comment together:

```yaml
name: Claude
on:
  issue_comment:
    types: [created]
permissions:
  contents: read
  pull-requests: write
  issues: write
  id-token: write
jobs:
  claude:
    name: claude
    if: contains(github.event.comment.body, '@claude')
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - name: Check out the default branch
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 1
      - name: Run Claude Code
        uses: anthropics/claude-code-action@34968b5981d5d170904281aa3df6f3c0d4a28855 # v1.0.249
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

Things to notice:

- `on: issue_comment` fires when a comment is created on an issue or a pull request.
- The `if:` line only looks at the comment text. It saves runner minutes. It is not the access check. The action does that itself.
- The top-level `permissions:` block lists four lines. Everything else becomes `none`. Compare it with the example workflow in the lesson: `contents` is `read` here, and there is no `actions: read`.
- `id-token: write` is not used by this exact file. With `github_token` and an API key, the action never asks for an identity token. It is only used on the default app path (no `github_token`) or with federation. We keep it so the file still works if you switch to one of those, and the checker looks for it. On its own it does not let the job change files.
- `github_token` makes the action use the job's own token, so the `permissions:` block is the real limit. Without it the action uses the Claude app's token, which can write.
- Both actions are pinned to a full commit SHA with the version in a comment. The `actions/checkout` pin is the same one this repo's `ci.yml` uses.
- The key comes from `${{ secrets.ANTHROPIC_API_KEY }}`. No key is written in the file. The secret does not exist, and you leave it that way.

## 4. Check the file yourself

The checker below is deliberately small. Before you commit, check these by eye:

- The event is `issue_comment`, and the job has the `if:` guard with `@claude`.
- The `permissions:` block is at the top level and has `contents: read`, `pull-requests: write`, `issues: write` and `id-token: write`.
- Every `uses:` line ends in 40 hex characters and a `# vX.Y.Z` comment.
- The action's `with:` has `github_token: ${{ secrets.GITHUB_TOKEN }}`.
- There is no API key, token or password anywhere in the file.

## 5. Open a pull request and merge it

```bash
git add .github/workflows/claude.yml
git commit -m "ci: add a pinned, switched-off claude workflow"
git push -u origin add-claude-workflow
gh pr create --fill
```

If you did GH2, your `checks` workflow runs on this pull request. Wait for it with `gh pr checks --watch`. Then merge. Your GH1 ruleset allows squash merges:

```bash
gh pr merge --squash --delete-branch
git switch main
git pull
```

## Check my work

Set `PRACTICE_REPO` in `.env`, then press **Check my work**. It runs read-only `gh` calls on the file on your default branch. It reads no secret, and your repo has none for this task:

- The file `.github/workflows/claude.yml` exists.
- It has a `uses:` line for `anthropics/claude-code-action` followed by `@` and a full 40-character hex SHA.
- It has the line `id-token: write`.
- It passes `github_token: ${{ secrets.GITHUB_TOKEN }}` to the action.
- It contains no string that starts with `sk-ant-`.

The checker cannot tell a commit SHA from a tag-object SHA, because both are 40 hex characters. Step 2 is how you make sure you pinned a commit. It also does not check the event, the guard or the other permissions. Step 4 covers those.
