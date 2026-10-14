---
id: gh5-secrets-and-permissions
track: github
title: "Secrets, GITHUB_TOKEN, permissions and environments"
minutes: 30
pins:
  gh: "2.102"
sources:
  - github-actions-concepts-security-secrets
  - github-actions-how-tos-write-workflows-choose-what-workflows-do-use-secrets
  - github-actions-concepts-security-github-token
  - github-actions-tutorials-authenticate-with-github-token
  - github-actions-reference-workflows-and-actions-workflow-syntax
  - github-actions-how-tos-deploy-configure-and-manage-deployments-manage-environments
  - github-actions-reference-security-secure-use
---
Your workflows run code on a machine you do not own. Some of that code must prove who it is, with an API key or with GitHub's own token. This lesson covers where secrets live, why hiding them in logs is not a plan, what the automatic `GITHUB_TOKEN` can do, how `permissions:` shrinks it, and how an environment puts a gate in front of a secret. You then read this repo's own CI and practise in your own repo. This site is not affiliated with GitHub. It teaches how GitHub works and links to the official pages.

One idea runs through all of it: give each job only the access it needs, and nothing more. This is called least privilege.

## What a secret is and where it lives

A secret is a named value that GitHub stores, encrypted, for your workflows. Use one for anything you would not put in a public file: an API key, a password, a token. ([Secrets](https://docs.github.com/en/actions/concepts/security/secrets))

A secret can live at three levels:

- **Repository secret.** Any workflow in that one repo can use it.
- **Environment secret.** It belongs to one environment of one repo (more below). Only a job that names that environment can use it.
- **Organization secret.** One value shared by many repos. You will not need this level.

You add a secret in the repo's Settings, or from the terminal. The CLI asks for the value at a prompt, so it never lands in a file or in your shell history. You cannot read it back later. ([Using secrets in GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets))

```bash
gh secret set API_KEY                  # repository secret; you type the value at the prompt
gh secret set API_KEY --env staging    # environment secret
gh secret list                         # names and dates only, never values
```

A job only gets a secret when a step asks for it with the `secrets` context:

```yaml
steps:
  - name: Call the service
    env:
      API_KEY: ${{ secrets.API_KEY }}
    run: ./call-service.sh
```

GitHub swaps `${{ secrets.API_KEY }}` for the real value just before the step runs, and the script reads it as `$API_KEY`. Put `env:` on the one step that needs the secret. If you put it at the top of the workflow, every step and every action can read it.

Three details that surprise people:

- **A missing secret is not an error.** A wrong name gives an empty string, and the step carries on with nothing.
- **Pull requests from forks and Dependabot runs do not get your secrets.** The `GITHUB_TOKEN` is the one exception.
- **Write access means read access.** Anyone who can push a workflow to your repo can write one that uses your secrets. A secret is only as private as the list of people who can write. ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use))

## Masking is not a vault

GitHub tries to hide secrets in logs. If a step prints the exact value of a secret, the log shows `***`. This is called redaction. It helps, but it is not a guarantee. ([Secrets](https://docs.github.com/en/actions/concepts/security/secrets), [Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use))

The runner looks for the exact text of the secret in the log and replaces it. Anything that changes the text slips past:

```bash
echo "$API_KEY"          # the log shows ***
echo "$API_KEY" | rev    # the log shows the value backwards, not hidden
```

There are more ways for a secret to escape:

- **The runner only knows the secrets this job uses.** A value you build from a secret, such as a signed token or an encoded copy, is not on its list. Register it yourself with `echo "::add-mask::$VALUE"`.
- **A secret that holds a block of JSON or YAML is hard to hide.** Make one secret per value.
- **The log is only one exit.** A step, or an action it uses, can send the value to a web server.
- **In a public repo, anyone can read the logs.** A leak is public the moment the step ends.

If a secret leaks, do not try to hide it. First revoke or rotate it where it was issued, so the old value stops working. Then store the new value in the GitHub secret, and delete the run's logs. Do it in that order, because someone may already have copied the old value.

Safe debugging means printing facts about a secret, not the secret. Is it empty? How long is it? Your practice task prints the length (`${#NAME}` is bash for the length of a variable). A length of 0 usually means a typo in a name:

```bash
echo "PRACTICE_TOKEN has ${#PRACTICE_TOKEN} characters"
```

## The token every job gets

On top of your own secrets, every job gets one more, called `GITHUB_TOKEN`. GitHub makes it for you, so you never store it. ([GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token))

- **It is automatic and scoped.** GitHub creates a new token for each job. It works on the repo that holds the workflow, and nowhere else.
- **It expires.** It stops working when the job ends, and after 6 hours at most on GitHub-hosted runners.
- **It is easy to reach.** You write it as `${{ secrets.GITHUB_TOKEN }}` or `${{ github.token }}`. An action can read it from `github.token` even if you never pass it in. ([Use GITHUB_TOKEN for authentication](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token)) So it is your job to keep it small.

One rule trips people up. **Things done with the `GITHUB_TOKEN` do not start new workflow runs.** Say a job pushes a commit with this token, and another workflow has `on: push`. That second workflow does not run. This is on purpose: it stops endless loops. A few events, such as `workflow_dispatch`, are exceptions. If you need the normal behaviour, use a GitHub App token or a personal access token, and handle the extra power with care.

## Shrinking the token with permissions

The `permissions:` key decides what the `GITHUB_TOKEN` may do. Each area, such as `contents`, `issues` or `pull-requests`, gets `read`, `write` or `none`. `write` includes `read`. ([Workflow syntax: `permissions`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#permissions))

```yaml
permissions:
  contents: read
```

Before you write anything, the token starts from a default setting for the repo: either "read and write" or "read only". Do not rely on it. To see yours, run this inside your practice repo folder and look for `default_workflow_permissions`:

```bash
gh api repos/{owner}/{repo}/actions/permissions/workflow
```

Now the rule that matters most. **Once you list any permission, every permission you did not list becomes `none`.** So `contents: read` on its own also takes away access to issues, pull requests and packages. If a step then fails with "Resource not accessible by integration", the token is missing a permission. Work out which area the step needs and add only that one.

You can put the key in two places:

- **At the top of the workflow.** It applies to every job.
- **Inside one job.** It applies to that job only, and it replaces the top-level block for that job. The "unlisted means none" rule works inside it too.

The shortcuts are `read-all`, `write-all`, and `{}`, which means no access at all. The good pattern is a small default at the top, and a bigger set in the one job that needs it:

```yaml
permissions:
  contents: read            # the default for every job

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "run the tests here"
  report:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      issues: write         # this job gets issues and nothing else
    steps:
      - run: gh issue create --repo "$GITHUB_REPOSITORY" --title "Tests ran" --body "Done"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

The `report` job has `issues: write` and nothing else. It does not check out the code, so it needs no more. If it did, you would add `contents: read` to its block too. The `gh` command reads its token from `GH_TOKEN`, so the step passes the `GITHUB_TOKEN` in under that name.

## Environments and protection rules

An environment is a named place that a job can target, such as `staging` or `production`. You create one in the repo's Settings, under Environments. It gives you two things. ([Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments))

**Protection rules.** These are gates that must pass before a job that uses the environment can start. You can require reviewers (one approval from up to 6 people or teams is enough), add a wait timer, and limit which branches or tags may use the environment. For example, only `main` can reach `production`.

**Environment secrets.** These exist only for jobs that name the environment, and a job can read them only after the rules pass. A repository secret has no gate: any job in any workflow can ask for it. So keep a powerful secret, such as a production deploy key, in an environment with rules in front of it.

A job names its environment with the `environment:` key. ([Workflow syntax: environment](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idenvironment))

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - run: ./deploy.sh
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
```

When the run reaches this job, GitHub holds it and checks the rules. Only when they all pass does it send the job to a runner, with the environment's secrets. Three things to know:

- **A typo does not fail.** If a job names an environment that does not exist, GitHub creates it on the spot, with no rules and no secrets. Your job then runs with an empty secret and no gate. Anyone who can edit workflows can create environments this way, but only repo admins can configure them.
- **Plans matter.** On a GitHub Free account, environments can only be configured for public repos. Your public practice repo is fine.
- **A reviewer gate needs a second person.** If you are alone in the repo, the reviewer is you.

## Least privilege in the Hint Kata CI

This repo's two workflow files use everything above. Open `.github/workflows/ci.yml` and `.github/workflows/evals.yml` and look for four habits.

1. **A small token, written down.** Both files have `permissions: contents: read` at the top level. Even if the repo default is already read only, the file says it, so a later change to that setting cannot widen the token.
2. **Pinned actions.** `actions/checkout` and `astral-sh/setup-uv` are pinned to a full commit SHA, with the version in a comment (see GH2). An action runs inside your job, so a hacked one could use the token and any secret the job holds. ([Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)) Dependabot opens a weekly pull request that updates the SHA and the comment together.
3. **One secret, used in one place.** `evals.yml` expects a repository secret named `OPENROUTER_API_KEY`. Only the one step that runs the evals gets it, through a step-level `env:`. The workflow starts by hand (`workflow_dispatch`), never from a pull request, so a pull request cannot start a run that spends money. `ci.yml` uses no secrets.
4. **A person sets the value.** The owner adds the secret with `gh secret set OPENROUTER_API_KEY`, typing the value at the prompt, never in a file, a pull request or a chat. This site's own policy is to put a spend cap on the key at the provider, so a leak has a ceiling.

The `POSTGRES_PASSWORD` in `ci.yml` guards a throwaway test database inside the job's machine. It protects nothing real, so it is not a secret.

## Secret scanning and push protection

Never put a secret in a file in the repo. In a public repo, anyone can read it the moment you push, and git keeps history. GitHub adds two safety nets. Secret scanning checks public repos for known kinds of secret and raises an alert. Push protection can block a push that contains a known secret, before it lands in the repo. Neither is a promise, because they only recognise the kinds of secret they know. If one fires, or you leak a secret by hand, rotate it first. Deleting the commit does not make it safe again. Hint Kata has both turned on.

Adapted from GitHub Docs, © GitHub, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Modified: summarized and adapted. Read 2026-10-14. Checked with `gh` 2.102. This site is not affiliated with GitHub.

**Sources:**
[Secrets](https://docs.github.com/en/actions/concepts/security/secrets),
[Using secrets in GitHub Actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets),
[GITHUB_TOKEN](https://docs.github.com/en/actions/concepts/security/github_token),
[Use GITHUB_TOKEN for authentication in workflows](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token),
[Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax),
[Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments),
[Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use).

**Further reading (not used as a source):**
[Secret scanning](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning),
[Push protection](https://docs.github.com/en/code-security/concepts/secret-security/push-protection).
