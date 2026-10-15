---
id: gh11-claude-in-github
track: github
title: "Claude in GitHub: claude-code-action and its security model"
minutes: 30
pins:
  gh: "2.102"
  claude-code-action: "v1.0.249"
sources:
  - claude-code-action-readme
  - claude-code-action-setup
  - claude-code-action-security
  - claude-code-action-examples-claude
  - claude-code-docs-github-actions
  - claude-code-docs-code-review
---
Some teams let an AI agent work inside GitHub. You write `@claude` in an issue or a pull request, and an agent reads the thread, answers, and sometimes pushes code. The action that does this is `claude-code-action`. This lesson explains what it does, how it is installed, what access it needs, who can start it, and what can go wrong when it reads text written by strangers. You then write a safe workflow file for it in your practice repo. You will not install anything and you will not add a secret. This site is not affiliated with Anthropic or GitHub. It teaches how the tool works and links to the official pages.

Two things to know before you start. First, this repo does **not** use the action, and one section below says why. Second, the lesson is built on GH5 (secrets and `permissions:`). If `permissions:` or `secrets.NAME` look strange, read GH5 first.

## What the action does

`claude-code-action` is a GitHub Action. A workflow in your repo calls it, and it runs on your own runner, the machine GitHub gives your job. It starts Claude Code there, with the issue or pull request as its context. The calls to the model go to the provider you choose: the Anthropic API directly, or Amazon Bedrock, Google Vertex AI or Microsoft Foundry. ([README](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/README.md))

The README says the action picks a mode from the situation your workflow is in. You do not set the mode yourself. Two situations matter most:

- **A mention.** Someone writes `@claude` in an issue, a comment or a review. Claude answers questions about the code, reviews the changes, or makes a small fix. The example workflow also supports an issue assigned to a chosen user, and a different trigger phrase in place of `@claude`. ([example workflow](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/examples/claude.yml))
- **A prompt.** You give the action a `prompt` input, a fixed instruction written in the workflow. The job then runs without anyone typing a mention. This is how automatic work is built, such as a review of every new pull request. The README lists "automatic PR code review" among its use cases and sends you to its solutions guide for the full workflows. That guide is not one of this site's cached sources, so follow the link from the README if you want it.

A second input, `claude_args`, passes options to Claude Code. The example file shows commented samples: a model name, `--max-turns` and `--allowedTools`.

While Claude works, the README says it shows a progress checklist that updates as tasks finish. By default it does not open pull requests itself. It commits to a new branch and gives you a link to the page where a person starts the pull request. ([Security](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/docs/security.md)) That keeps a human between a bot's change and a merge.

Anthropic also documents this from the Claude Code side, and has its own code-review feature. Those pages have no reuse licence, so this lesson does not copy them. See the linked pages: [Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions) and [Code Review](https://code.claude.com/docs/en/code-review).

## How it gets installed

The quickest way is from your terminal. Open `claude` and run `/install-github-app`. It walks you through installing the GitHub app and adding the secret. You must be a repository admin to do it, because installing an app and adding a secret are both admin actions. This shortcut is only for people who use the Anthropic API directly. The cloud providers have their own guide. ([README](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/README.md))

The manual way has three steps. ([Setup guide](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/docs/setup.md))

1. Install the Claude GitHub app on the repo.
2. Add one secret. Either `ANTHROPIC_API_KEY`, or `CLAUDE_CODE_OAUTH_TOKEN`. The guide says people on Pro and Max plans can make the second one by running `claude setup-token` on their own computer.
3. Copy the example workflow into `.github/workflows/`.

Two rules for the secret. **It lives in the repo's secrets, never in a file.** The workflow only names it: `anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}`. The guide calls a pasted key in the YAML the wrong way to do it, and tells you to rotate keys now and then and to never log them. This is the same advice as GH5, with an extra reason: in a public repo, the workflow file is public. Add the secret with the hidden prompt of `gh secret set`, as GH5 shows. In this project the build agents are not even allowed to run `gh secret` (see `docs/HARNESS.md`). A person types the value.

**The token choice matters.** The guide offers both and does not compare what they cost you. It only says where the OAuth token comes from. The sources here do not say which limits that token uses; see the linked Claude Code pages.

The guide also describes two ways to avoid a stored key or the shared app. ([Setup guide](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/docs/setup.md))

- **Workload identity federation.** The job swaps GitHub's short-lived identity token for a short-lived Anthropic one, so no `ANTHROPIC_API_KEY` secret exists. The setup is done once in the Claude Console by an organization admin. The ids you put in the workflow are identifiers, not credentials. If you also set a static key, the key wins and federation is not used.
- **Your own GitHub app.** You create an app with only the permissions you want, and pass its token to the action in `github_token`. This is for when policy forbids a third-party app.

## The permissions the workflow grants

The example workflow gives the job five permissions. ([example workflow](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/examples/claude.yml))

```yaml
permissions:
  contents: write
  pull-requests: write
  issues: write
  id-token: write
  actions: read   # Required for Claude to read CI results on PRs
```

Read each line with GH5 in mind. Once you list a permission, every unlisted one becomes `none`.

- **`contents`.** Files, commits and branches. The security page says the app uses it to read files and to create branches. The example gives `write` so Claude can push a branch.
- **`pull-requests` and `issues`.** Reading threads, posting or updating comments, and (for `pull-requests`) creating or updating pull requests. Both are `write` in the example.
- **`id-token: write`.** This one is easy to miss. It lets the job ask GitHub for an identity token (OIDC). The setup guide says the action uses it to fetch that token, and that the default path through the GitHub app already needs it. Without it the action cannot prove who it is, and by default that proof is how the job gets its write-capable token (see below).
- **`actions: read`.** The comment in the file says this lets Claude read CI results on pull requests. Leave it out, and by the GH5 rule that access is `none`. That is a reading of the comment and the GH5 rule. We did not run the action to see it fail.

**Which token does Claude use?** By default the action does not use the job's `GITHUB_TOKEN`. It uses `id-token: write` to get a short-lived token from the Claude app, and that token's access comes from the app's own permissions, not from your `permissions:` block. The security page lists them: Contents, Pull requests and Issues, each read and write. ([Security](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/docs/security.md)) So in the default setup, a small `permissions:` block does not limit Claude. To make the block the real limit, pass `github_token: ${{ secrets.GITHUB_TOKEN }}` to the action. The security page says that token is scoped to the job's declared permissions. The other way is your own GitHub app with fewer permissions, as in the setup guide. We did not run the action to test either route.

For your practice file you will use a smaller set than the example: `contents: read` where the example has `write`, and no `actions: read`, and you pass `github_token: ${{ secrets.GITHUB_TOKEN }}` so those lines apply. The point of the lesson is that you choose these lines on purpose. Reading and commenting need less than pushing code.

The example's `if:` has one branch per event. The branch for issue comments is the other thing to notice. It runs the job only when the comment holds `@claude`:

```yaml
if: contains(github.event.comment.body, '@claude')
```

That line saves runner minutes, so a job does not start for every comment. It is not a security control. Anyone can type `@claude`. The real check is the next section.

## Who can trigger it

Only people with write access. The security page says the action checks this for issue, pull request, comment and review events, and for `workflow_run` events it checks both the person behind the workflow and the person who started the earlier run. Manual runs, `repository_dispatch` and schedules are not checked again, because GitHub already needs write access to start a manual run and a schedule has no outside person. ([Security](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/docs/security.md))

So a stranger on a public repo can type `@claude` in an issue, and the `if:` line will match. The action then looks at who wrote it, sees no write access, and stops.

Three switches can weaken this. Read each as a warning.

- **Bots.** By default, apps and bots cannot trigger the action. `allowed_bots` lets named bots in. The page warns that allowed bots are not checked for write access. On a public repo, an app that anyone made may be able to open issues or comment. With `allowed_bots: '*'`, any such app could send the action a prompt. Prefer an explicit list of names you trust.
- **Non-write users.** `allowed_non_write_users` lets people without write access trigger the action. The page calls it a significant risk, for workflows that hold very few permissions, such as one that only adds issue labels. It needs the workflow's own `GITHUB_TOKEN`, not a personal access token. The page says a long-lived token could be partly or fully recovered over time through prompt injection.
- **Events that carry secrets.** `pull_request_target` and `workflow_run` run with the base repo's secrets. The page says never check out an untrusted pull-request ref into the workspace before the action. Check out the base branch, or check the head out into a subfolder.

What about pull requests from forks? For the ordinary `pull_request` event, GitHub does not hand secrets to a fork's run, as GH5 explains. So `ANTHROPIC_API_KEY` is empty there, and an action that needs it has nothing to use. That is a GitHub rule, not something this action adds. The two events above are the ones that do carry secrets, and that is why the page treats them with care.

## The prompt-injection surface

Here is the part that makes this tool different from a linter. The action sends text from the issue or pull request to a language model. Whoever wrote that text can try to give the model orders. This is called prompt injection. The model cannot always tell your instructions from instructions hidden in the data.

The write-access check does not solve it. It decides who may *start* the run. It does not decide who *wrote the words* Claude reads. A maintainer can type `@claude, summarize this pull request` on a pull request written by a stranger, and the stranger's text is now in Claude's context.

The security page names the tricks: instructions in HTML comments, invisible characters, and hidden HTML attributes. The action removes several kinds of hidden content before the model sees it: HTML comments, invisible characters, image alt text, hidden attributes and HTML entities. The page then says in plain words that new ways around this may appear. So treat the filter as one layer. The page asks you to read the raw text of anything from outside contributors before you let Claude process it. ([Security](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/docs/security.md))

The documented mitigations, from cheapest to strongest:

- **Narrow who is heard.** On public repos, `include_comments_by_actor` lists the users whose comments reach Claude. `exclude_comments_by_actor` drops noisy bots. If a user is in both, exclusion wins. ([Security](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/docs/security.md))
- **Narrow what Claude can do.** Limit the tools in `claude_args` with `--allowedTools`, as the example file shows. The page recommends this for workflows that admit non-write users.
- **Narrow the token.** Pass `GITHUB_TOKEN` with a small `permissions:` block, or use your own app with fewer permissions. If an injection works, it can only use what the token can do. This is least privilege from GH5. The page says the Claude app's token is short-lived and for the one repo only, but its access is the app's, not your block's.
- **Keep secrets out of the model's reach.** With `allowed_non_write_users`, the action scrubs Anthropic, cloud and Actions secrets from the environment of the programs it starts, as a best effort. The page says this reduces the risk and does not remove it. You can also cap how many times a helper script may run per job with `CLAUDE_CODE_SCRIPT_CAPS`.
- **Do not print everything.** `show_full_output` is off by default, because it would log tool output, which can hold secrets or file contents. In a public repo those logs are public. GitHub's step debug mode turns it on by itself, so do not leave debug on.
- **Keep a human in the loop.** The action does not open pull requests by default, and its commits are unsigned unless you turn on signing.

One more trap sits in the pull-request flow. The action restores a fixed list of Claude settings files from the base branch before it starts: the `.claude/` folder, `.mcp.json`, `CLAUDE.md` and a few more. A pull request cannot swap in its own versions. But the rest of the checkout, such as `package.json` or a `Makefile`, stays as the pull request wrote it. A hook in your trusted settings that runs `npm run format` would run the pull request's script. The page says to keep such commands self-contained.

## Pinning the action to a commit

The example workflow says `uses: anthropics/claude-code-action@v1`. A tag like `v1` is a label that points at a commit, and the owner can move it. Your job gives that action your `GITHUB_TOKEN` and any secret you pass it. If someone moves the tag to bad code, your next run runs the bad code. GH5 told you why: an action runs inside your job. So you pin to a full commit SHA, which cannot be moved.

Look up the SHA of a release tag with the CLI. The first command is the one most people try. Watch what it returns on this repo:

```bash
gh api repos/anthropics/claude-code-action/git/ref/tags/v1.0.249 --jq '.object'
```

On 2026-10-14 it printed `"type": "tag"` and the SHA `12732ed86c7c48cf319dc8c528fa0b24c81c3486`. That is the SHA of the **tag object**, not of the commit. The release tags here are annotated, which means the tag is its own small object that points at the commit. (The same lookup for `v1` showed `"type": "tag"` too.) Follow the pointer one more step:

```bash
gh api repos/anthropics/claude-code-action/git/tags/12732ed86c7c48cf319dc8c528fa0b24c81c3486 --jq '.object'
```

That printed `"type": "commit"` and the SHA `34968b5981d5d170904281aa3df6f3c0d4a28855`. This is the value for `uses:`. There is a shorter route that gives the commit straight away:

```bash
gh api repos/anthropics/claude-code-action/commits/v1.0.249 --jq '.sha'
```

Use whichever you like, but always check the `type`. A tag that is not annotated points at the commit directly. The release `v1.0.249` was the newest numbered one on the day this lesson was written, and the page files this site cached come from the same commit.

Then write the pin with the version in a comment, like this repo's `ci.yml` does:

```yaml
uses: anthropics/claude-code-action@34968b5981d5d170904281aa3df6f3c0d4a28855 # v1.0.249
```

The comment is for people and for Dependabot, which can update the SHA and the comment together. The SHA is what runs. Neither the lookup nor the workflow checker can tell you the commit is the right one. Compare it with the release page, and re-check when you update.

## Why Hint Kata said no, for now

This repo teaches the action and does not run it. The rejected list in `docs/HARNESS.md` gives two reasons.

1. **Shared usage limits.** The rejected list in `docs/HARNESS.md` (read 2026-10-14) records that the action would use the same usage limits as Claude Code on the owner's Mac. The note does not say how. We assume the owner would use the OAuth token from `claude setup-token`, which the setup guide says comes from a Pro or Max plan. A busy issue thread could then use up the allowance that the build work needs. The sources in this lesson do not state how limits are shared, so treat this as an observation about this repo, and see the linked Claude Code pages for your own plan.
2. **A public injection surface.** The repo is public. Anyone can open an issue or write a comment, and all of that text is untrusted. Even with the write-access check, the repo would have an agent that reads strangers' words and holds a token that can write.

Neither reason says the tool is bad. They are a trade-off for this project, for now, and the choice can change. Our reading is that an API key with a spend cap at the provider, a short allow-list of commenters, `github_token` with a small `permissions:` block and a pinned SHA would address most points in this lesson.

That is the exercise in the task. You write the file as if you would turn it on, with the guards in place, and you leave it switched off: no app, no secret. If someone commented `@claude` on that repo, the job would start and the secret would be empty. We expect the run to fail, and we did not try it. Do not try it either.

Adapted from the claude-code-action repository (MIT, © Anthropic); Claude Code docs linked only. Read 2026-10-14 at commit 34968b5 (release v1.0.249). Checked with `gh` 2.102. This site is not affiliated with Anthropic or GitHub.

**Sources:**
[Claude Code Action README](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/README.md),
[Setup guide](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/docs/setup.md),
[Security](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/docs/security.md),
[Example workflow (claude.yml)](https://github.com/anthropics/claude-code-action/blob/34968b5981d5d170904281aa3df6f3c0d4a28855/examples/claude.yml).

**Linked only (no reuse licence, nothing copied):**
[Claude Code GitHub Actions](https://code.claude.com/docs/en/github-actions),
[Code Review](https://code.claude.com/docs/en/code-review).

**Further reading (not used as a source):**
[Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use),
[Security hardening for GitHub Actions: using third-party actions](https://docs.github.com/en/actions/reference/security/secure-use#use-third-party-actions).
