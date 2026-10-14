# GitHub plans, rulesets, Actions and public-repo automation

_Research archive. Checked against primary sources on 2026-10-14. Facts about fast-moving tools (Claude Code, Pydantic AI, FastAPI, GitHub, OpenRouter) go stale quickly: re-check before relying on a number._

- **Needed by:** Phase 1 (bootstrap + CI)
- **Licence / attribution notes:** GitHub Docs: CC-BY-4.0.
- **Covers:** Free vs Pro on public repos, solo-friendly ruleset JSON, security features, CodeQL default setup, auto-merge mechanics, Dependabot (uv), pinned action SHAs, 2026 behaviour changes, claude-code-action verdict, gh CLI commands

## GitHub plans and features (Oct 2026): Free vs Pro on private repos, rulesets for a solo maintainer, Actions pricing and scheduling, gh CLI, GitHub MCP server, and anthropics/claude-code-action

**Summary.** On a personal account, GitHub Free only gives branch protection, rulesets and CODEOWNERS enforcement on PUBLIC repos. On PRIVATE repos you need GitHub Pro. Pro costs $4/month in third-party and older official sources; the current github.com/pricing page no longer lists Pro by name. Merge queue is not available to personal accounts at all: it needs an org-owned public repo or GitHub Enterprise Cloud. Environment required reviewers and wait timers stay public-only even on Pro. GitHub's docs state that a PR author cannot approve their own PR. So the solo-friendly ruleset sets the approval count to 0 and still requires a PR, required status checks, linear history, and blocks force-push and deletion. The admin role (RepositoryRole actor_id 5) can bypass only through a PR. Actions gives 2,000 minutes/month on Free and 3,000 on Pro for private repos. Public repos and self-hosted runners are free. Hosted-runner prices dropped on 2026-01-01 (Linux 2-core is now $0.006/min). The $0.002/min self-hosted platform fee announced in Dec 2025 was postponed with no new date. Scheduled workflows now accept an optional IANA `timezone` key, run at most every 5 minutes, can be delayed or dropped at the top of the hour, and auto-disable after 60 days without activity in public repos. Version churn matters. actions/checkout is at v7. astral-sh/setup-uv is at v10.3.0 and has published NO floating major tags since v8, so `@v10` will not resolve. github-mcp-server reached v2.0.x. claude-code-action is still `@v1` (v1.0.249). The remote GitHub MCP server (https://api.githubcopilot.com/mcp/) works for every GitHub user with a PAT Bearer header and does not need a Copilot subscription, except for Copilot-specific tools. claude-code-action authenticates with an API key, a subscription OAuth token (`claude setup-token`), workload identity federation, or Bedrock/Vertex/Foundry. Each run costs Actions minutes plus tokens, or subscription usage.

### Findings

- **GitHub Pro (personal) costs $4/month. The current github.com/pricing page shows only Free ($0), Team ($4/user/month, labeled 'for individuals and organizations', with a '*first 12 months' footnote) and Enterprise ($21). Pro is not named there.** [medium, load-bearing]
  The $4 Pro price comes from GitHub's 2020 plan-change FAQ (https://docs.github.com/en/get-started/learning-about-github/faq-about-changes-to-githubs-plans) and 2026 third-party guides. No current official page shows a Pro price. Confirm it in Settings > Billing & Licensing > Upgrade before printing a price in lessons. The upgrade path 'Under Pro on the Compare plans page, click Upgrade to Pro' is still documented at https://docs.github.com/en/billing/how-tos/manage-plan-and-licenses/upgrade-plan
  Source: <https://github.com/pricing>
- **Rulesets, classic protected branches and CODEOWNERS are available in PUBLIC repos on GitHub Free, and in public AND private repos on GitHub Pro, Team and Enterprise Cloud. A private repo on a Free personal account cannot enforce branch protection, required reviews, required status checks or code-owner review.** [high, load-bearing]
  Exact banner: 'Rulesets are available in public repositories with GitHub Free and GitHub Free for organizations, and in public and private repositories with GitHub Pro, GitHub Team, and GitHub Enterprise Cloud.' The same pattern applies to protected branches (https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) and CODEOWNERS (https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners). Push rulesets need the Team plan. Limit: 75 rulesets per repo. Rulesets and classic branch protection layer together, and the strictest rule wins.
  Source: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets>
- **Environments: Free gets them only in public repos. Pro and Team get environments, environment secrets and deployment branches in private repos. Other deployment protection rules (required reviewers, wait timer) are public-repo-only on Free, Pro and Team.** [high, load-bearing]
  Quote: 'If you are on a GitHub Free, GitHub Pro, or GitHub Team plan, other deployment protection rules, such as a wait timer or required reviewers, are only available for public repositories.'
  Source: <https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments>
- **Merge queue is available only in public repos owned by an ORGANIZATION, or in private org repos on GitHub Enterprise Cloud. Personal-account repos cannot use it.** [high]
  Quote: 'Pull request merge queues are available in any public repository owned by an organization, or in private repositories owned by organizations using GitHub Enterprise Cloud.'
  Source: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue>
- **PR authors cannot approve their own PRs, so a solo maintainer must set required_approving_review_count to 0. Owners and admins can merge without an approving review.** [high, load-bearing]
  Quote: 'Pull request authors cannot approve their own pull requests.' Also: 'Require a pull request before merging ... The pull request doesn't necessarily have to be approved, but it must be opened' (https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets). A new default adds one extra required approval for unattributed Copilot PRs, but it has no effect when 0 approvals are required.
  Source: <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/reviewing-proposed-changes-in-a-pull-request>
- **Ruleset REST schema (POST /repos/{owner}/{repo}/rulesets). Required: name, enforcement (disabled|active|evaluate; evaluate is Enterprise-only). target defaults to branch. bypass_actors[] holds actor_id, actor_type (Integration|OrganizationAdmin|RepositoryRole|Team|DeployKey|User) and bypass_mode (always|pull_request|exempt). conditions.ref_name.include/exclude accept ~DEFAULT_BRANCH and ~ALL.** [high, load-bearing]
  Rule types: deletion, non_fast_forward, required_linear_history (type only). pull_request has REQUIRED booleans/ints: dismiss_stale_reviews_on_push, require_code_owner_review, require_last_push_approval, required_approving_review_count, required_review_thread_resolution, plus optional allowed_merge_methods [merge|squash|rebase]. required_status_checks takes required_status_checks[{context, integration_id?}], strict_required_status_checks_policy (required) and do_not_enforce_on_create (optional). OrganizationAdmin does not apply to personal repos. The `gh api` help's own example is `gh api repos/{owner}/{repo}/rulesets --input file.json`. The GitHub Actions app id is 15368, verified with `gh api /apps/github-actions`; use it as integration_id to pin checks to Actions.
  Source: <https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset>
- **For bypass_actors with actor_type RepositoryRole, the base role IDs are maintain=2, write=4, admin=5.** [medium, load-bearing]
  This mapping is not in docs.github.com REST reference. It comes from GitHub's integrations org Terraform provider docs ('at the time of writing'). Verify after creation with `gh api repos/OWNER/REPO/rulesets/ID` and check that the bypass entry shows repository_role_name admin. Alternative: actor_type User with the numeric user ID.
  Source: <https://github.com/integrations/terraform-provider-github/blob/main/docs/resources/repository_ruleset.md>
- **The current REST API version is 2026-03-10. Requests without the X-GitHub-Api-Version header default to 2022-11-28. Previous versions stay supported for at least 24 months after a new one ships.** [high, load-bearing]
  The rulesets reference page now shows 'X-GitHub-Api-Version: 2026-03-10' in its examples. I did not check whether 2026-03-10 changed the ruleset payload, so pin the header explicitly in scripts.
  Source: <https://docs.github.com/en/rest/about-the-rest-api/api-versions>
- **'Require linear history' only works if the repo allows squash or rebase merging. It blocks merge commits on the target branch.** [high]
  The same page notes that job names used as required status checks must be unique across workflows, or results become ambiguous and merges get blocked (see the about-protected-branches tip).
  Source: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets>
- **Actions included usage for private repos: Free gets 2,000 min/month, 500 MB artifact storage and 10 GB cache per repo. Pro gets 3,000 min/month, 1 GB artifact storage and 10 GB cache per repo. Standard hosted runners are free in public repos, and self-hosted runners are free.** [high, load-bearing]
  Discrepancy: the plans page (https://docs.github.com/en/get-started/learning-about-github/githubs-plans) says Pro includes '2 GB of GitHub Packages storage', but the Actions billing table says Pro artifact storage is 1 GB, shared with Packages. Codespaces: Free 120 core-hours/15 GB, Pro 180/20 GB. Without a payment method, usage is BLOCKED once the quota runs out, so a learner gets no surprise bill. Copilot code review now consumes Actions minutes on private repos.
  Source: <https://docs.github.com/en/billing/concepts/product-billing/github-actions>
- **Hosted-runner prices were cut by up to 39% on 2026-01-01. Current rates: Linux 2-core x64 $0.006/min, Linux 1-core $0.002, Linux arm64 2-core $0.005, Windows 2-core $0.010, macOS $0.062. The $0.002/min self-hosted 'cloud platform charge' announced for 2026-03-01 was POSTPONED with no new date.** [high, load-bearing]
  Update text: 'We're postponing the announced billing change for self-hosted GitHub Actions to take time to re-evaluate our approach.' Current rates are at https://docs.github.com/en/billing/reference/actions-runner-pricing, and the billing docs still say self-hosted usage is free. Overage storage: $0.25/GB-month for artifacts and Packages, $0.07 for cache.
  Source: <https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions/>
- **The schedule trigger uses 5-field POSIX cron and runs in UTC by default, but now accepts an optional `timezone` (IANA string) per cron entry. The shortest interval is every 5 minutes. Runs can be delayed at high load, especially at the start of every hour, and some queued jobs may be dropped. It runs only from the default branch. In PUBLIC repos it auto-disables after 60 days without repository activity. @daily-style macros are not supported.** [high, load-bearing]
  The `timezone` key is new compared with older knowledge. During DST spring-forward, skipped times move to the next valid time. `github.event.schedule` tells you which cron fired. workflow_dispatch also needs the workflow file on the default branch to show the 'Run workflow' button.
  Source: <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule>
- **concurrency supports group plus cancel-in-progress, and a NEW optional `queue` property: `single` (default, at most one pending) or `max` (up to 100 pending). `queue: max` combined with `cancel-in-progress: true` is a validation error. Group names are case-insensitive.** [high, load-bearing]
  permissions: if you specify access for any permission, all unspecified permissions become `none`. It can be set at top level or per job. pull_request_target gets a read/write GITHUB_TOKEN even from forks.
  Source: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency>
- **Secrets vs variables: variables are for non-sensitive config, are exposed through the `vars` context and are NOT masked in logs. Secrets are encrypted client-side with libsodium sealed boxes, are only readable when a workflow references them, and can be scoped to org, repo or environment. Environment secrets can be gated behind required reviewers. OIDC lets a job exchange a short-lived token with a cloud provider instead of storing long-lived secrets, and needs `id-token: write`.** [high]
  Variables: https://docs.github.com/en/actions/concepts/workflows-and-actions/variables. OIDC: https://docs.github.com/en/actions/concepts/security/openid-connect. claude-code-action also uses OIDC (id-token: write) for its default GitHub App auth and for Anthropic workload identity federation.
  Source: <https://docs.github.com/en/actions/concepts/security/secrets>
- **actions/checkout current release is v7.0.1 (2026-07-20), and the floating `v7` tag exists and matches v7.0.1. v7 refuses to check out fork PR code under pull_request_target or workflow_run unless you set `allow-unsafe-pr-checkout: true`. v6 moved persisted credentials into $RUNNER_TEMP. v5 moved to node24.** [high, load-bearing]
  Verified with `gh api repos/actions/checkout/releases` and the tag refs. Anthropic's own claude-code-action examples still use actions/checkout@v6, which works but is one major behind. actions/setup-python is at v7.0.0.
  Source: <https://github.com/actions/checkout>
- **astral-sh/setup-uv current release is v10.3.0 (2026-10-09). Since v8.0.0 the project NO LONGER publishes floating major or minor tags (@v8, @v10, @v10.3), so `uses: astral-sh/setup-uv@v10` will fail to resolve. Pin `@v10.3.0` or the commit SHA.** [high, load-bearing]
  The README now shows `uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0`. The last floating tag is v7. Releases are immutable. v10.0.0 breaking change: with the default `enable-cache: auto`, the cache is DISABLED for pull_request_target, workflow_run and release events. It adds `version: latest-known` and reads the Python version from .tool-versions.
  Source: <https://github.com/astral-sh/setup-uv/releases/tag/v8.0.0>
- **gh CLI is at v2.102.0 (2026-09-30). `gh ruleset` is READ-ONLY, with subcommands list, view and check, so you create rulesets with `gh api`. Key flags: `gh repo create NAME --private --source=. --remote=origin --push`. `gh pr create` takes --fill/--title/--body/--base/--draft. `gh pr checks` takes --watch, --required and --fail-fast. `gh pr view` takes --comments/--json/--web. `gh pr merge` takes -s/--squash, -d/--delete-branch, --auto and --admin.** [high, load-bearing]
  Verified from local `gh --help` output for v2.102.0. `gh pr merge --admin` 'Use administrator privileges to merge a pull request that does not meet requirements'. With a merge queue, --admin bypasses it. --auto needs auto-merge enabled in repo settings. `gh ruleset check <branch>` shows the rules that apply, which is useful for a lesson task.
  Source: <https://cli.github.com/manual/gh_ruleset>
- **The remote GitHub MCP server URL is https://api.githubcopilot.com/mcp/ and PAT auth uses the header `Authorization: Bearer <PAT>`. For read-only mode, append `/readonly` to the URL or send `X-MCP-Readonly: true`. Toolsets can be chosen by URL (/x/{toolset}) or with the X-MCP-Toolsets header. Other headers: X-MCP-Tools, X-MCP-Lockdown, X-MCP-Insiders.** [high, load-bearing]
  Toolsets include actions, code_security, git, governance (rulesets), issues, pull_requests, repos, users and others, plus remote-only copilot_spaces and github_support_docs_search. Latest release is v2.0.2 (2026-10-08). v2.0.0 added typed structured outputs that are advertised only to clients on the MCP 2026-07-28 spec. Lockdown mode is 'a best-effort content filter, not a security boundary'.
  Source: <https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md>
- **The GitHub MCP server does NOT require a Copilot subscription. It is 'available to all GitHub users regardless of plan type'. Only tools tied to paid features need that license, for example Copilot cloud agent tools or GHAS code scanning.** [high, load-bearing]
  Quote: 'If a feature requires a paid GitHub or Copilot license, the equivalent MCP tool will require the same subscription.' The Claude Code install guide (https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-claude.md) uses `claude mcp add-json github '{...}'` for Claude Code 2.1.1+.
  Source: <https://docs.github.com/en/copilot/how-tos/provide-context/use-mcp/set-up-the-github-mcp-server>
- **anthropics/claude-code-action: use `@v1`. The latest release is v1.0.249 (2026-10-14), and the v1 tag points to the same commit. Auth options are `anthropic_api_key`, `claude_code_oauth_token` (Claude Pro, Max, Team or Enterprise subscription, generated with `claude setup-token`), workload identity federation (anthropic_federation_rule_id + anthropic_organization_id via GitHub OIDC), and use_bedrock/use_vertex/use_foundry.** [high, load-bearing]
  Costs per run: GitHub Actions minutes on hosted runners, plus API tokens. With an OAuth token, runs use the Claude subscription instead of API billing. Docs advise --max-turns in claude_args, job timeouts and concurrency to cap cost. Quick setup is `/install-github-app` in Claude Code, which needs repo admin and an authenticated gh. Workflows need `id-token: write` for the default Claude GitHub App auth. Commits made with the default GITHUB_TOKEN don't trigger CI, so leave github_token unset to use the app. A static API key or OAuth token takes precedence over federation inputs (https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md).
  Source: <https://code.claude.com/docs/en/github-actions>
- **In claude-code-action, automation mode starts when a `prompt` input is given. Without a prompt, the action waits for '@claude'. The triggering user needs write access, and bot actors are rejected unless listed in `allowed_bots`. On public repos, secrets are withheld from fork PRs, so automatic reviews only run on same-repo branches.** [high]
  The official review pattern is either the solutions-guide prompt with `mcp__github_inline_comment__create_inline_comment` plus `gh pr comment`, or the code-review plugin (`plugins: code-review@claude-code-plugins`, prompt `/code-review:code-review --comment ...`). The inline-comment MCP server starts only when `--allowedTools` in claude_args names it.
  Source: <https://code.claude.com/docs/en/github-actions>

### Exact snippets (copied from the sources named)

**Solo-maintainer ruleset (constructed from the REST schema; not a verbatim docs example) + gh api call** — <https://docs.github.com/en/rest/repos/rules#create-a-repository-ruleset>

```bash
cat > ruleset.json <<'EOF'
{
  "name": "protect-default-branch",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [
    { "actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "pull_request" }
  ],
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    { "type": "pull_request", "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": true,
        "allowed_merge_methods": ["squash"]
    } },
    { "type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": true,
        "do_not_enforce_on_create": false,
        "required_status_checks": [ { "context": "test", "integration_id": 15368 } ]
    } }
  ]
}
EOF
gh api --method POST \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2026-03-10" \
  repos/{owner}/{repo}/rulesets --input ruleset.json
# verify
gh ruleset list
gh ruleset check main
```

**Scheduled workflow cron (verbatim from docs, including the new timezone key)** — <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule>

```yaml
on:
  schedule:
    - cron: '30 5 * * 1-5'
      timezone: "America/New_York"
```

**astral-sh/setup-uv usage (verbatim README; no floating @v10 tag exists)** — <https://github.com/astral-sh/setup-uv>

```yaml
- name: Install the latest version of uv
  uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
```

**Minimal Python CI for the ruleset's 'test' check (constructed; versions verified 2026-10-14)** — <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency>

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
      - run: uv sync --locked
      - run: uv run pytest
```

**claude-code-action automatic PR review, basic (verbatim from Solutions Guide)** — <https://github.com/anthropics/claude-code-action/blob/main/docs/solutions.md>

```yaml
name: Claude Auto Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      id-token: write
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 1

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            REPO: ${{ github.repository }}
            PR NUMBER: ${{ github.event.pull_request.number }}

            Please review this pull request with a focus on:
            - Code quality and best practices
            - Potential bugs or issues
            - Security implications
            - Performance considerations

            Note: The PR branch is already checked out in the current working directory.

            Use `gh pr comment` for top-level feedback.
            Use `mcp__github_inline_comment__create_inline_comment` (with `confirmed: true`) to highlight specific code issues.
            Only post GitHub comments - don't submit review text as messages.

          claude_args: |
            --allowedTools "mcp__github_inline_comment__create_inline_comment,Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*)"
```

**Add remote GitHub MCP server to Claude Code with a PAT (verbatim)** — <https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-claude.md>

```bash
claude mcp add-json github '{"type":"http","url":"https://api.githubcopilot.com/mcp","headers":{"Authorization":"Bearer YOUR_GITHUB_PAT"}}'
```

**Remote GitHub MCP optional headers: toolsets + read-only (verbatim)** — <https://github.com/github/github-mcp-server/blob/main/docs/remote-server.md>

```json
{
    "type": "http",
    "url": "https://api.githubcopilot.com/mcp/",
    "headers": {
        "X-MCP-Toolsets": "repos,issues",
        "X-MCP-Readonly": "true",
        "X-MCP-Lockdown": "false"
    }
}
```

**gh CLI solo PR flow (repo create example verbatim from gh help; rest are documented flags)** — <https://cli.github.com/manual/gh_repo_create>

```bash
# Create a remote repository from the current directory
gh repo create my-project --private --source=. --remote=upstream
# (add --push to push local commits; use --remote=origin for the usual name)
gh pr create --fill --base main
gh pr checks --watch --required
gh pr view --comments
gh pr merge --squash --delete-branch
```

### Recommendations
- For the GitHub track's hands-on tasks, have learners use PUBLIC practice repos. That way rulesets, required checks and CODEOWNERS work on GitHub Free. Say plainly that private-repo enforcement needs Pro (about $4/month; confirm in billing settings).
- Teach rulesets as the main tool and classic branch protection as legacy. Use the solo ruleset: require a PR with 0 approvals, required status check 'test' pinned to integration_id 15368, block deletion and force-push, linear history, squash-only, and an admin bypass in pull_request mode for emergencies via `gh pr merge --admin`.
- Frame the AI reviewer (claude-code-action or Claude Code Review) as the 'second pair of eyes' that leaves comments without gating the merge. GitHub forbids self-approval, and a bot approval should not replace human judgment.
- Pin actions to exact versions or SHAs in lesson code and in the site's own CI: actions/checkout@v7 (or SHA) and astral-sh/setup-uv@v10.3.0 or its SHA. Add Dependabot for github-actions so the bumps are visible. Never write setup-uv@v10.
- Schedule the docs re-sync off the hour, e.g. cron '17 3 * * 1', and add workflow_dispatch for manual runs. If the site repo is public, keep it active or the schedule auto-disables after 60 days. Treat a missed or dropped run as normal, with idempotent jobs.
- Use concurrency groups with cancel-in-progress on CI, an explicit minimal `permissions:` block, and timeout-minutes on every job, so a learner on the 2,000 or 3,000 free minutes never exhausts the quota.
- Store DATABASE_URL (Neon), LLM API keys and Vercel tokens as Actions secrets, preferably environment secrets. Keep non-sensitive values (model names, docs URLs) as variables. Mention OIDC as the next step, and that claude-code-action already uses it.
- For the 'Claude Code + MCP' lesson, connect the remote GitHub MCP server with a fine-grained PAT scoped to one repo and the /readonly URL (or X-MCP-Readonly: true) first. Turn on write tools later. Stress that no Copilot subscription is needed.
- For claude-code-action on a solo budget, the learner can use `claude setup-token` (subscription OAuth) instead of a metered API key if they have Pro or Max. Otherwise use an API key with `--max-turns` and a spend limit. Note that either way it also burns Actions minutes on private repos.
- Date-stamp each GitHub-track lesson ('verified 2026-10'). Have the scheduled re-sync also check release tags (checkout, setup-uv, claude-code-action, github-mcp-server, gh) so lessons are flagged when majors change.

### Risks
- The Pro price ($4/month) is not shown on any current official GitHub page I could fetch. Pricing pages now promote 'Team ... for individuals and organizations' with a 12-month promo footnote, so the personal Pro offer may be changing.
- RepositoryRole admin = actor_id 5 comes from the Terraform provider docs, not the REST reference. A wrong ID makes the POST fail with 422 or bypass the wrong role. Verify after creation.
- REST API version 2026-03-10 is now current. I did not check whether it changed ruleset payloads, and examples written against 2022-11-28 may behave differently if the header is pinned.
- If the required status check context name doesn't match the actual job name, or two workflows reuse the same job name, every PR is blocked or ambiguous. Beginners hit this often.
- setup-uv's removal of floating tags and checkout v7's refusal to check out fork PRs under pull_request_target will break copy-pasted older tutorials. Anthropic's own examples still show checkout@v6.
- The self-hosted runner platform fee ($0.002/min) was postponed, not cancelled, and could return in a revised form.
- Scheduled workflows can be delayed or dropped under load, so a docs re-sync must not be assumed to run exactly on time.
- A Claude subscription OAuth token is tied to one person's subscription and its usage limits. API-key runs are metered. Prompt-injection from PR content is a real risk on public repos: keep allowed tools minimal and don't use pull_request_target with untrusted code.
- GitHub MCP lockdown mode is explicitly 'not a security boundary'. A broad classic PAT in an MCP config gives the agent full account access.

### Open questions
- Will the learning-site repo itself be public or private? This decides whether Free is enough for rulesets and whether the 60-day schedule auto-disable applies.
- Should GitHub-track exercises run in learner-owned public repos, or in a template repo the site provides?
- What is the exact current price and availability of personal GitHub Pro? Confirm in Settings > Billing & Licensing on the learner's account.
- Did REST API version 2026-03-10 change any ruleset fields? Test one POST with and without the header.
- Does the learner have a Claude Pro or Max subscription (OAuth token path), or will claude-code-action use a metered API key?
- Should the site's own CI include an automatic Claude PR review, or only an @claude-on-demand workflow, to save minutes and tokens?

### Fact-check (second agent re-read the sources)

I checked everything on 2026-10-14. Sources were the live docs.github.com article bodies and rendered HTML, the github/rest-api-description OpenAPI file (api.github.com.2026-03-10.deref.json), GET-only gh api calls (releases, tags, branches, /apps/github-actions), local gh 2.102.0 --help, raw READMEs and docs from the action repos, the github.com/pricing HTML, and code.claude.com/docs/en/github-actions.md. Claim 4 is the only correction. Rulesets do not exempt admins by default; they bypass only when listed in bypass_actors. Classic branch protection does exempt admins by default. With a count of 0, anyone with write access can merge. All 8 snippets matched their sources or the official schema. The only notes are plan and workflow caveats, with no field, nesting or format mismatches. Scratch downloads are in (session scratchpad)

Corrections:
- [corrected] PR authors cannot approve their own PRs, so a solo maintainer must set required_approving_review_count to 0. Owners and admins can merge without an approving review. The Copilot extra approval has no effect at 0. → Three parts are confirmed: authors cannot approve their own PRs, a PR 'doesn't necessarily have to be approved, but it must be opened', and the Copilot extra approval 'has no effect if the ruleset requires zero approvals'. The admin part is wrong for rulesets. Admins are not exempt by default and can bypass only when they are in bypass_actors. Admins are exempt by default only under classic branch protection, unless 'Do not allow bypassing the above settings' is on. With a count of 0, anyone with write access can merge, not only admins. A solo maintainer can also keep a count of 1 or more and add an admin RepositoryRole bypass with bypass_mode pull_request, so a count of 0 is not the only option. (<https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository>)

Snippet checks:
- Snippet 1 (ruleset JSON + gh api): no schema mismatches against OpenAPI 2026-03-10. All keys, nesting, enums and required pull_request/required_status_checks params are valid, and bypass_mode pull_request is valid for a branch ruleset. Caveat, not a schema error: a private repo on a Free personal account cannot enforce the ruleset (it needs Pro, or the repo must be public). Caveat: the admin bypass with bypass_mode pull_request already lets the admin merge without approval, so required_approving_review_count 0 is redundant (harmless).
- Snippet 2 (schedule with timezone): none. It matches the docs example word for word.
- Snippet 3 (setup-uv SHA pin): none. It matches the README word for word, and the SHA resolves to v10.3.0.
- Snippet 4 (Python CI): none. The keys are valid. actions/checkout@v7 resolves. The setup-uv SHA is valid. Job id 'test' produces the check-run name 'test', which matches the ruleset context. Minor caveat: workflow-level cancel-in-progress: true also cancels in-flight runs on main when another push lands.
- Snippet 5 (Claude Auto Review): none. It matches docs/solutions.md 'Basic Example (No Tracking)' word for word, and all inputs exist in action.yml.
- Snippet 6 (claude mcp add-json): none. It matches install-claude.md line 37 word for word (URL without trailing slash, as in the guide).
- Snippet 7 (remote MCP headers JSON): none. It matches remote-server.md word for word.
- Snippet 8 (gh solo PR flow): none for flags. The repo create line and its comment match gh 2.102.0 help word for word, and --fill, --base, --watch, --required, --comments, --squash and --delete-branch all exist. Caveat: without --push the branch is not on the remote yet, so gh pr create will prompt to push.

## GitHub setup for a public personal repo (GitHub Pro owner) using gh CLI 2.102 and REST API 2026-03-10: plan features, repo settings, rulesets, security features, CodeQL, auto-merge, issues and milestones, Dependabot with uv, pinned action versions, a uv CI job, gotchas, and claude-code-action

**Summary.** On a public repo, every feature you asked about is already free on GitHub Free: rulesets, required status checks, auto-merge, secret scanning, push protection, Dependabot alerts and security updates, CodeQL code scanning, and Actions minutes on standard runners. Pro's extras (3,000 Actions minutes, required reviewers, wikis and code owners) apply to private repos. For this project the only Pro benefit that matters is the bigger Codespaces quota (180 core-hours and 20 GB, against 120 and 15 on Free), and only if you use Codespaces. Merge queue is not available on repos owned by a personal account, Pro or not. You can do the whole setup with gh 2.102 plus `gh api`. One catch: gh sends `X-GitHub-Api-Version: 2022-11-28` by default, so add `-H "X-GitHub-Api-Version: 2026-03-10"` to any call that should use the newer version. CodeQL default setup (one PATCH call, languages python and actions) is simpler than an advanced codeql.yml. To make merges depend on it, use a ruleset `code_scanning` rule rather than a required status check. Current pinned versions are actions/checkout v7.0.1, astral-sh/setup-uv v10.3.0 (no floating `v10` tag exists) and github/codeql-action v4.38.3; the exact SHAs are listed below. Dependabot supports `uv` for both version updates (GA since 2025-03-13) and security updates (since 2025-12-16), as well as `github-actions`. Two GitHub behaviours changed in 2026. PRs created with GITHUB_TOKEN now produce workflow runs that wait for approval instead of not running at all. Public repos may also have suspicious workflow runs held until someone approves them in a browser. If claude-code-action runs with CLAUDE_CODE_OAUTH_TOKEN, it draws on your Claude subscription, and that subscription's limits are shared with local Claude Code. It adds no capacity and adds a public prompt-injection surface, so it is not worth it for someone who already runs out of weekly usage.

### Findings

- **Rulesets, protected branches and auto-merge are free on public repos under GitHub Free; Pro only extends them to private repos.** [high]
  About rulesets says they are available in public repositories with GitHub Free and in public and private repositories with GitHub Pro. The auto-merge page uses the same wording. Rulesets can stack (several apply at once). The REST docs mark 'evaluate' enforcement as GitHub Enterprise only, so use 'active'.
  Source: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets>
- **Secret scanning runs automatically and for free on public repos. Push protection for your own user account is on by default. Push protection for the repository is off by default and an admin has to turn it on.** [high]
  The enabling-secret-scanning page says: 'Public repositories: Secret scanning runs automatically for free.' The push protection page splits it in two: protection for users is enabled by default and stops you pushing secrets to public repos, while protection for repositories is disabled by default and anyone with write access can bypass it by giving a reason. gh 2.102 has `gh repo edit --enable-secret-scanning --enable-secret-scanning-push-protection`, and the same settings exist in PATCH /repos security_and_analysis.
  Source: <https://docs.github.com/en/code-security/secret-scanning/introduction/about-push-protection>
- **Code scanning (CodeQL) is free on public repositories, and Dependabot security updates are available on all repositories.** [high]
  About code scanning: available for 'Public repositories on GitHub.com'; private repos need a Code Security license. The Dependabot security updates page says: 'All repositories on GitHub'. Enable alerts with PUT /repos/{o}/{r}/vulnerability-alerts, which also turns on the dependency graph. Enable security updates with PUT /repos/{o}/{r}/automated-security-fixes.
  Source: <https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning>
- **Actions minutes on standard GitHub-hosted runners are free for public repos; Pro's 3,000-minute quota only counts for private repos. The one Pro benefit relevant here is the larger Codespaces quota.** [high]
  The Actions billing page says minutes stay free for public repositories, and the plan quotas (Pro: 3,000 minutes, 1 GB artifacts) are for private repositories. Codespaces billing gives personal Pro accounts 180 core-hours and 20 GB-month per month, against 120 and 15 on Free. The plans page lists Pro's other extras (required reviewers, code owners, wikis, insights) as private-repo tools only.
  Source: <https://docs.github.com/en/billing/concepts/product-billing/github-actions>
- **Merge queue is not available on repos owned by a personal account, whether public or private.** [high]
  Managing a merge queue: 'available in any public repository owned by an organization, or in private' repositories on enterprise plans. To keep PRs up to date you have two options. One is `gh pr update-branch` with allow_update_branch=true. The other is to turn off the strict 'up to date' policy.
  Source: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-a-merge-queue>
- **`gh repo create NAME --public --source=. --remote=origin --push` works on an existing folder, but only if the folder is a git repo with at least one commit.** [high]
  In the gh v2.102.0 source (pkg/cmd/repo/create/create.go), a folder without git fails with 'current directory is not a git repository. Run `git init`'. A repo with no commits fails with '`--push` enabled but no commits found'. No README is added unless you pass --add-readme.
  Source: <https://github.com/cli/cli/blob/v2.102.0/pkg/cmd/repo/create/create.go>
- **gh 2.102 sends `X-GitHub-Api-Version: 2022-11-28` by default. To use 2026-03-10 you have to pass the header yourself, and a header you pass with `gh api -H` replaces the default.** [high]
  gh api/client.go sets apiVersionValue = "2022-11-28". go-gh's headerRoundTripper does not overwrite a header the request already has. The API versions page lists 2026-03-10 as current, with 2022-11-28 supported until 10 March 2028. Breaking changes in 2026-03-10 that touch this setup: `use_squash_pr_title_as_default` is removed from repo settings (use squash_merge_commit_title), `merge_commit_sha` is removed from PR payloads, and the `javascript`/`typescript` values are removed from the default-setup languages enum (use `javascript-typescript`).
  Source: <https://docs.github.com/en/rest/about-the-rest-api/breaking-changes?apiVersion=2026-03-10>
- **The merge settings in PATCH /repos/{o}/{r} are allow_squash_merge, allow_merge_commit, allow_rebase_merge, allow_auto_merge (default false), delete_branch_on_merge (default false) and allow_update_branch, plus squash_merge_commit_title (PR_TITLE or COMMIT_OR_PR_TITLE) and squash_merge_commit_message (PR_BODY, COMMIT_MESSAGES or BLANK).** [high]
  gh 2.102 has equivalent flags: --enable-auto-merge, --delete-branch-on-merge, --enable-squash-merge, --enable-merge-commit=false, --enable-rebase-merge=false, --allow-update-branch and --squash-merge-commit-message {default|pr-title|pr-title-commits|pr-title-description}.
  Source: <https://docs.github.com/en/rest/repos/repos?apiVersion=2026-03-10#update-a-repository>
- **Ruleset REST schema: the pull_request rule has five required parameters, required_status_checks needs strict_required_status_checks_policy plus a list of {context, integration_id}, and deletion and non_fast_forward take no parameters. 15368 is the correct integration ID for GitHub Actions.** [high]
  Endpoint: POST /repos/{o}/{r}/rulesets. Required pull_request parameters: dismiss_stale_reviews_on_push, require_code_owner_review, require_last_push_approval, required_approving_review_count and required_review_thread_resolution. Optional: allowed_merge_methods ('merge', 'squash', 'rebase'). `conditions.ref_name.include` accepts '~DEFAULT_BRANCH'. I confirmed the app ID with `gh api /apps/github-actions`, which returns id 15368. A separate `code_scanning` rule takes code_scanning_tools [{tool, alerts_threshold: none|errors|errors_and_warnings|all, security_alerts_threshold: none|critical|high_or_higher|medium_or_higher|all}].
  Source: <https://docs.github.com/en/rest/repos/rules?apiVersion=2026-03-10#create-a-repository-ruleset>
- **Leave bypass_actors empty. Your agents act with your gh token, so any bypass you hold, they hold too.** [medium]
  bypass_mode can be always, pull_request or exempt. The repository admin role is RepositoryRole actor_id 5, but GitHub's docs don't list that value; it comes from the Terraform provider docs and github/rest-api-description#4406. With no bypass actors, `gh pr merge --admin` cannot get around the PR or status-check rules. To recover in an emergency, set the ruleset's enforcement to 'disabled'.
  Source: <https://github.com/github/rest-api-description/issues/4406>
- **Pitfalls with required check names: a check that never reports blocks the merge. A workflow skipped by path, branch or commit-message filters leaves its required check Pending. A skipped job counts as success. Checks from workflow_dispatch runs don't count for the PR.** [high]
  From the troubleshooting doc: skipped-by-filter checks stay Pending and show 'Waiting for status to be reported'. A check posted by a different app than the one required shows 'Required status check "build" was not set by the expected GitHub App.' The status-checks doc says a skipped job reports 'Success' even when it is required. The context name is the check run name, which is normally the job's `name:` (or the job id). After the first run, confirm the exact name with `gh api repos/O/R/commits/SHA/check-runs --jq '.check_runs[].name'`.
  Source: <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks>
- **CodeQL default setup is simpler than an advanced codeql.yml: one PATCH call, no workflow file, and it scans pushes to the default branch, PRs against it (except from forks) and once a week.** [high]
  PATCH /repos/{o}/{r}/code-scanning/default-setup takes state configured|not-configured, query_suite default|extended, threat_model remote|remote_and_local, runner_type, and languages (actions, c-cpp, csharp, go, java-kotlin, javascript-typescript, python, ruby, swift). It returns 200 or 202 (202 includes a run_id). Advanced setup generates a workflow file you then maintain, using github/codeql-action.
  Source: <https://docs.github.com/en/code-security/concepts/code-scanning/setup-types>
- **Default setup posts a 'Code scanning results' check with a result per tool ('Code scanning results / CodeQL') that fails on error, critical or high findings. To block merges on it, use the ruleset `code_scanning` rule (tool 'CodeQL') rather than a required status check.** [high]
  The triage doc says the 'Code scanning results' check holds the results for every configuration and fails on findings of severity error, critical or high. The merge-protection doc configures this through rulesets ('Require code scanning results', or the code_scanning rule in REST). That rule blocks a PR while the analysis is still running, or when the tool is not configured at all. The check runs come from the 'GitHub Advanced Security' app (id 57789, from `gh api /apps/github-advanced-security`).
  Source: <https://docs.github.com/en/code-security/code-scanning/managing-your-code-scanning-configuration/set-code-scanning-merge-protection>
- **`gh pr merge --auto` merges right away when the PR's merge state is CLEAN, HAS_HOOKS or UNSTABLE; otherwise it turns on auto-merge. In auto-merge mode, `--delete-branch` deletes nothing, either locally or on GitHub, so branch cleanup depends on the repo's delete_branch_on_merge setting.** [high]
  From the gh v2.102.0 source (pkg/cmd/pr/merge/merge.go): isImmediatelyMergeable covers CLEAN, HAS_HOOKS and UNSTABLE. deleteLocalBranch and deleteRemoteBranch both return early when autoMerge is set. The docs add three preconditions: the repo must allow auto-merge, only users with write access can turn it on for a PR, and the option appears only on PRs that cannot be merged immediately. Auto-merge switches off if someone without write access pushes to the head branch.
  Source: <https://github.com/cli/cli/blob/v2.102.0/pkg/cmd/pr/merge/merge.go>
- **Since gh 2.99, `gh pr merge --delete-branch` knows about git worktrees. When it merges immediately, it may remove a clean linked worktree that has the PR branch checked out.** [high]
  cli/cli#14007 was merged on 2026-08-21 and shipped in v2.99.0; it closed #3442. Per the PR description, gh removes another linked worktree before deleting its branch, and skips local cleanup with a warning when the worktree is dirty or the base branch is checked out elsewhere. Deleting the remote branch still happens.
  Source: <https://github.com/cli/cli/pull/14007>
- **With strict 'require branches to be up to date' turned on, auto-merge waits on any PR that falls behind main, and GitHub does not update the branch for you. With several parallel agent PRs, every merge forces the others through an update and a full CI rerun.** [medium]
  Troubleshooting doc: when up-to-date is required, the base branch must be merged or rebased in. gh 2.102 has `gh pr update-branch [--rebase]`, and allow_update_branch enables the update button. Merge queue is the usual fix but is not available on personal repos. For a solo repo, strict=false plus CI on every push to main is a reasonable trade-off: you accept a small risk that two individually green PRs conflict semantically. The trade-off itself is my analysis; GitHub's docs don't state it.
  Source: <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks>
- **Labels, milestones and issues: `gh label create` (with --force to update), milestones only through REST (gh has no milestone command), and `gh issue create --milestone <title> --label <name>`.** [high]
  Milestone endpoint: POST /repos/{o}/{r}/milestones with title (required), state open|closed, description, and due_on (YYYY-MM-DDTHH:MM:SSZ). `gh milestone` returns 'unknown command' in 2.102. `gh issue create -m` takes the milestone name, and -l can be repeated.
  Source: <https://docs.github.com/en/rest/issues/milestones?apiVersion=2026-03-10#create-a-milestone>
- **'Closes #N' in a PR body links the PR and closes the issue on merge, but only when the PR targets the default branch.** [high]
  The keywords are close, closes, closed, fix, fixes, fixed, resolve, resolves and resolved. Keywords in commit messages also close issues once the commit lands on the default branch. With squash_merge_commit_message=PR_BODY, the keyword is also carried into the squash commit.
  Source: <https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue>
- **Dependabot supports `package-ecosystem: "uv"` for version updates (GA 2025-03-13) and security updates (2025-12-16). The docs table lists uv as supported at 'v0.11'. `github-actions` is also supported. groups and cooldown work for both.** [high]
  In the github/docs source (data/reusables/dependabot/supported-package-managers.md), the uv row shows version updates and security updates as supported. Groups take patterns, exclude-patterns, update-types (minor|patch|major), dependency-type and applies-to. Cooldown has a default of 3 days for version updates, works with uv and GitHub Actions, and does not apply to security updates. The latest uv is 0.13.1, while the docs list support at v0.11.
  Source: <https://github.blog/changelog/2025-12-16-dependabot-security-updates-now-support-uv>
- **Current pinned action versions: actions/checkout v7.0.1 = 3d3c42e5aac5ba805825da76410c181273ba90b1; astral-sh/setup-uv v10.3.0 = 1c37ad07a6a961277cf70c0d37d6f313000f5884 (released 2026-10-09, no floating major tag); github/codeql-action v4.38.3 = 24c54180a607b1449ed407dd24f251e4e9147c8d (the v4 tag points to the same commit); anthropics/claude-code-action v1.0.249 = 34968b5981d5d170904281aa3df6f3c0d4a28855.** [high]
  Checked on 2026-10-14 with `gh api repos/.../git/ref/tags/...`, dereferencing annotated tags. setup-uv only has tags v10.0.0, v10.0.1, v10.1.0, v10.2.0 and v10.3.0, and its README pins to that SHA. CodeQL also keeps a v3 line (v3.38.3), but v4 is the current major.
  Source: <https://github.com/astral-sh/setup-uv/releases/tag/v10.3.0>
- **Recent breaking changes: setup-uv v10 turns the cache off for pull_request_target, workflow_run and release events; v9 changed the prune-cache default to false. checkout v7 refuses to check out fork PR code under pull_request_target or workflow_run unless you set allow-unsafe-pr-checkout: true.** [high]
  From the setup-uv v10.0.0 and v9.0.0 release notes and the actions/checkout README 'Checkout v7' section. Neither affects an ordinary `pull_request` CI job. uv's own docs recommend pinning the uv version, for example `version: "0.13.1"`.
  Source: <https://github.com/actions/checkout/releases/tag/v7.0.0>
- **The GITHUB_TOKEN rule has changed: PRs created or updated by a workflow using GITHUB_TOKEN now create pull_request runs that wait for approval, rather than no runs at all. PRs that local Claude Code opens with your own gh login trigger CI normally.** [high]
  Trigger-a-workflow doc: such runs wait in an 'approval-required' state until someone with write access clicks 'Approve workflows to run'. A PAT or GitHub App token avoids the approval step. Changelog of 2026-06-11: 'Bot-created pull requests can run workflows if approved'. Pushes made with GITHUB_TOKEN still don't trigger push workflows.
  Source: <https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow>
- **In public repos, scheduled workflows are disabled automatically after 60 days with no repository activity. Since July 2026, GitHub also holds workflow runs it flags as potentially malicious on public repos until a collaborator approves them in a logged-in browser session.** [high]
  The disable/enable doc covers the 60-day rule. Changelog of 2026-07-28: the hold applies automatically, cannot be configured, and covers public repositories on github.com only; the criteria are not published. An unattended agent cannot approve a held run.
  Source: <https://github.blog/changelog/2026-07-28-github-actions-holds-unproven-workflows-for-approval>
- **If claude-code-action authenticates with CLAUDE_CODE_OAUTH_TOKEN (from `claude setup-token`, valid one year), it bills your Claude subscription, and that usage counts against the same 5-hour and weekly limits as local Claude Code.** [high]
  Claude Code docs: 'If you authenticate with an OAuth token, runs use your Claude subscription instead of API billing.' The help center says Pro and Max limits 'are shared across Claude and Claude Code, meaning all activity in both tools counts against the same limits', and that usage on all surfaces counts toward the same limit. Running on GitHub-hosted runners in a public repo costs no Actions minutes.
  Source: <https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan>
- **claude-code-action on a public repo: by default only users with write access and non-bot actors can trigger it. Fork PRs get no secrets on `pull_request`. Prompt injection through issue and comment content is the main remaining risk, and Actions logs are public.** [high]
  From the action's security.md. allowed_non_write_users and allowed_bots='*' are marked risky. Content is sanitized (HTML comments, invisible characters and similar are stripped), but 'new bypass techniques may emerge'. Use include_comments_by_actor to allowlist commenters. For PRs, `.claude/` and CLAUDE.md are restored from the base branch, but lockfiles and Makefiles stay at the PR head. Keep show_full_output off because public logs leak data. Code Review docs: on public repos, fork PRs get no secrets, so reviews run only for same-repo branches.
  Source: <https://github.com/anthropics/claude-code-action/blob/main/docs/security.md>

### Exact snippets (copied from the sources named)

**1. Create the public repo from the local folder (needs git init plus at least one commit)** — <https://github.com/cli/cli/blob/v2.102.0/pkg/cmd/repo/create/create.go>

```
git init -b main && git add -A && git commit -m "chore: initial scaffold with CI"
gh repo create NAME --public --source=. --remote=origin --push --description "Local-first learning site"
```

**2a. Repo merge settings (gh flags)** — <https://cli.github.com/manual/gh_repo_edit>

```
gh repo edit OWNER/NAME --enable-auto-merge --delete-branch-on-merge --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false --allow-update-branch --squash-merge-commit-message pr-title-description
```

**2b. Same settings via REST 2026-03-10 (-F sends real booleans)** — <https://docs.github.com/en/rest/repos/repos?apiVersion=2026-03-10#update-a-repository>

```
gh api -X PATCH repos/OWNER/NAME -H "X-GitHub-Api-Version: 2026-03-10" \
  -F allow_auto_merge=true -F delete_branch_on_merge=true \
  -F allow_squash_merge=true -F allow_merge_commit=false -F allow_rebase_merge=false \
  -F allow_update_branch=true -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=PR_BODY
```

**3. Branch ruleset on the default branch (create after the first CI run on main; 'checks' must exactly match the CI job name)** — <https://docs.github.com/en/rest/repos/rules?apiVersion=2026-03-10#create-a-repository-ruleset>

```
gh api -X POST repos/OWNER/NAME/rulesets -H "X-GitHub-Api-Version: 2026-03-10" --input - <<'EOF'
{
  "name": "protect-default-branch",
  "target": "branch",
  "enforcement": "active",
  "bypass_actors": [],
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "pull_request", "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": false,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false,
        "allowed_merge_methods": ["squash"]
    } },
    { "type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": false,
        "do_not_enforce_on_create": false,
        "required_status_checks": [ { "context": "checks", "integration_id": 15368 } ]
    } }
  ]
}
EOF
# Optional, once CodeQL default setup has finished its first analysis, add this to "rules":
# { "type": "code_scanning", "parameters": { "code_scanning_tools": [ { "tool": "CodeQL", "alerts_threshold": "errors", "security_alerts_threshold": "high_or_higher" } ] } }
gh ruleset check main -R OWNER/NAME   # confirm which rules apply
```

**4. Secret scanning, push protection, Dependabot alerts and security updates** — <https://docs.github.com/en/rest/repos/repos?apiVersion=2026-03-10>

```
gh api -X PATCH repos/OWNER/NAME -H "X-GitHub-Api-Version: 2026-03-10" --input - <<'EOF'
{"security_and_analysis":{"secret_scanning":{"status":"enabled"},"secret_scanning_push_protection":{"status":"enabled"}}}
EOF
gh api -X PUT repos/OWNER/NAME/vulnerability-alerts -H "X-GitHub-Api-Version: 2026-03-10"
gh api -X PUT repos/OWNER/NAME/automated-security-fixes -H "X-GitHub-Api-Version: 2026-03-10"
gh api repos/OWNER/NAME --jq .security_and_analysis   # verify
```

**5. CodeQL default setup (python plus actions)** — <https://docs.github.com/en/rest/code-scanning/code-scanning?apiVersion=2026-03-10#update-a-code-scanning-default-setup-configuration>

```
gh api -X PATCH repos/OWNER/NAME/code-scanning/default-setup -H "X-GitHub-Api-Version: 2026-03-10" --input - <<'EOF'
{"state":"configured","languages":["python","actions"],"query_suite":"default"}
EOF
gh api repos/OWNER/NAME/code-scanning/default-setup   # check state
```

**6. Actions hardening (optional)** — <https://docs.github.com/en/rest/actions/permissions?apiVersion=2026-03-10>

```
gh api -X PUT repos/OWNER/NAME/actions/permissions/workflow -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false
gh api -X PUT repos/OWNER/NAME/actions/permissions/fork-pr-contributor-approval -f approval_policy=all_external_contributors
# Optional: require SHA-pinned actions (test that CodeQL default setup still runs afterwards)
gh api -X PUT repos/OWNER/NAME/actions/permissions -F enabled=true -f allowed_actions=all -F sha_pinning_required=true
```

**7. Labels, milestones, issues, PR, auto-merge** — <https://docs.github.com/en/rest/issues/milestones?apiVersion=2026-03-10#create-a-milestone>

```
gh label create "type:feature" --color 1D76DB --description "New capability" --force
gh label create "area:tutor" --color 5319E7 --description "Tutor agent" --force
gh api -X POST repos/OWNER/NAME/milestones -H "X-GitHub-Api-Version: 2026-03-10" -f title="M1 Local MVP" -f state=open -f description="FastAPI+Jinja2+SQLite+tutor" -f due_on="2026-11-30T23:59:59Z"
gh issue create --title "Quiz grader agent" --body "..." --label "type:feature" --label "area:tutor" --milestone "M1 Local MVP"
gh pr create --base main --title "feat: quiz grader" --body "Closes #12"
gh pr merge 34 --auto --squash --delete-branch   # with --auto, --delete-branch is a no-op; delete_branch_on_merge cleans up the remote branch
```

**8. .github/dependabot.yml** — <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>

```
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
    cooldown:
      default-days: 7
    groups:
      python-minor-patch:
        patterns: ["*"]
        update-types: ["minor", "patch"]
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      actions:
        patterns: ["*"]
```

**9. .github/workflows/ci.yml (job name 'checks' is the required-check context)** — <https://docs.astral.sh/uv/guides/integration/github/>

```
name: CI
on:
  pull_request:
  push:
    branches: [main]
permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
jobs:
  checks:
    name: checks
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false
      - uses: astral-sh/setup-uv@1c37ad07a6a961277cf70c0d37d6f313000f5884 # v10.3.0
        with:
          version: "0.13.1"
          enable-cache: true
      - run: uv sync --locked --all-extras --dev
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy .        # or: uv run pyright / uv run ty check (ty is still Beta, 0.0.87)
      - run: uv run pytest -q
```

**10. Verify the exact check-run names before writing the ruleset** — <https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/troubleshooting-required-status-checks>

```
gh api repos/OWNER/NAME/commits/$(git rev-parse HEAD)/check-runs --jq '.check_runs[] | [.name, .app.id] | @tsv'
```

### Recommendations
- Order of operations: (1) commit the scaffold together with ci.yml and dependabot.yml; (2) run `gh repo create --public --source=. --push`; (3) set the repo merge settings; (4) enable secret scanning, push protection, Dependabot alerts and security updates; (5) enable CodeQL default setup; (6) wait for the first CI run on main and read the exact check-run name; (7) create the ruleset; (8) create labels, milestones and issues.
- Pass -H "X-GitHub-Api-Version: 2026-03-10" on every `gh api` call, because gh 2.102 defaults to 2022-11-28.
- Use strict_required_status_checks_policy=false. Merge queue isn't available on personal repos, and strict mode makes every parallel agent PR update its branch and rerun CI after each merge. If you do turn strict on, have the agent run `gh pr update-branch` before waiting on auto-merge.
- Leave bypass_actors empty, and add Claude Code permission deny rules (in settings.json) for `gh api -X DELETE*`, `gh api */rulesets*`, `gh repo edit*`, `gh pr merge --admin*`, and any change to security_and_analysis. Your agents use your admin token and could otherwise loosen the guardrails themselves.
- Don't put path filters on the required CI workflow, because skipped workflows leave the required check Pending forever. Name the job explicitly (`name: checks`) and keep the name stable.
- Use CodeQL default setup instead of an advanced codeql.yml. Gate merges on it with a ruleset `code_scanning` rule (tool CodeQL, errors / high_or_higher), added only after the first analysis has finished. Don't add it as a required status check.
- Pin every action to a full SHA with a version comment (setup-uv has no v10 floating tag), and let Dependabot's github-actions ecosystem bump them. Pin the uv version in setup-uv.
- Rely on repo-level delete_branch_on_merge for branch cleanup. In worktrees, remember that gh 2.99+ `--delete-branch` may remove a clean linked worktree when a merge happens immediately.
- Dependabot PRs won't auto-merge unless a reviewer agent or a small workflow runs `gh pr merge --auto --squash`. GitHub's documented pattern uses dependabot/fetch-metadata (latest v3.1.0) gated on update-type.
- Skip claude-code-action for now. It draws from the same subscription limits that are already running out, and it adds a public prompt-injection surface. Keep reviews in local Claude Code subagents. If you add it later, use an API key with a spending cap, keep the default write-access-only triggers, leave allowed_non_write_users and allowed_bots unset, set include_comments_by_actor to just your username, and leave show_full_output off.

### Risks
- The autonomous agents run with your gh token, which has admin rights on the repo, so they can delete or disable the ruleset, change security settings or merge with --admin unless Claude Code permissions deny those commands.
- Anyone with write access, including your agents, can bypass repository push protection by giving a reason. Push protection is not an absolute guarantee against committing secrets.
- A ruleset `code_scanning` rule blocks every PR while the CodeQL analysis is still running, or if default setup is disabled or failing. A misspelled required-check context blocks every PR indefinitely ('Waiting for status to be reported').
- Actions logs on public repos are world-readable. Never echo secrets, and keep claude-code-action's show_full_output off. Debug mode turns full output on automatically.
- GitHub may hold 'potentially malicious' workflow runs on public repos (since July 2026), and only a human in a logged-in browser session can approve them. This can stall the autonomous auto-merge loop, for example after agents edit workflow files.
- Since the 2026-06-11 change, PRs created by workflows using GITHUB_TOKEN wait for manual approval. Any future automation that opens PRs from inside Actions will stall without a PAT or GitHub App token.
- GitHub's docs list Dependabot uv support at v0.11 while uv is at 0.13.1. A lockfile or feature mismatch could make Dependabot uv runs fail; watch the Dependabot logs after the first run.
- ty is still Beta (0.0.87). The pyright PyPI wrapper downloads Node at runtime, which adds a source of CI flakiness. mypy (2.4.0, Stable) is the lowest-risk choice for a required check.
- If claude-code-action is ever added with CLAUDE_CODE_OAUTH_TOKEN, every run uses up the same weekly quota. A one-year token stored as a repo secret is also a long-lived credential exposed to prompt injection.

### Open questions
- Is CodeQL default setup's weekly scan subject to the 60-day inactivity auto-disable that applies to scheduled workflows in public repos? I couldn't verify this.
- Does sha_pinning_required=true interfere with CodeQL default setup's dynamic workflows or with Dependabot jobs? It isn't documented; test before relying on it.
- Does the 2026-06-11 approval requirement cover only github-actions[bot] PRs or all bot-created PRs? The changelog wording is ambiguous.
- What exactly triggers a hold under the July 2026 'potentially malicious workflow' protection, and can an agent that edits .github/workflows set it off? The criteria are not published.
- Does Dependabot handle uv 0.13.x lockfiles cleanly, given the docs still list v0.11? I couldn't verify this.
- Is the repository admin role's RepositoryRole actor_id = 5 stable? GitHub's docs don't publish it; it is only community-verified. This matters only if you add a bypass actor.
- Is repo-level `security_and_analysis.secret_scanning` already 'enabled' by default on a new personal public repo? The docs only say scanning 'runs automatically'. The PATCH is idempotent either way; check with `gh api repos/O/R --jq .security_and_analysis`.
