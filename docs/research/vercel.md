# Vercel research

_Research archive. Checked against primary sources on 2026-10-14. Facts about fast-moving tools (Claude Code, Pydantic AI, FastAPI, GitHub, OpenRouter) go stale quickly: re-check before relying on a number._

- **Needed by:** Phase 2
- **Licence / attribution notes:** Vercel docs cited by link.
- **Covers:** Python/FastAPI runtime, limits, Fluid compute, Services (beta), previews, env vars, Deployment Protection, domains, Hobby vs Pro, AI Gateway, MCP

## Vercel (Oct 2026) for a FastAPI + Pydantic AI learning site: Python runtime, one-project frontend+backend, previews/protection/env/domains/Neon, pricing, AI Gateway, MCP

**Summary.** Vercel deploys FastAPI with zero configuration. It looks for a FastAPI instance named `app` in app.py, index.py, server.py, main.py, wsgi.py or asgi.py, at the project root or inside src/ or app/. You can point it somewhere else with `[tool.vercel] entrypoint = "module:app"` in pyproject.toml. Supported Python versions are 3.12 (the default), 3.13 and 3.14. Dependencies can come from pyproject.toml (with or without uv.lock), requirements.txt or Pipfile, and uv is the default installer. The whole FastAPI app runs as one Fluid compute function with streaming on by default. On Hobby the limit is 300s and 2 GB memory; on Pro the default is 300s, configurable up to 800s (1800s in beta), with up to 4 GB memory. A Python bundle can be 500 MB uncompressed (5 GB in the "Large Functions" beta), and request or response bodies are capped at 4.5 MB. To run a frontend and FastAPI in one project, Vercel documents "Services": a `services` key plus `rewrites` to `{service: ...}` in vercel.json. Services are labelled Beta on all plans, and the older `experimentalServices` key is being replaced. The non-beta alternatives are FastAPI serving a built static frontend through `app.frontend()`, or two separate projects. Preview deployments are created for every non-production branch push and every PR. Environment variables are scoped to Production, Preview (optionally per branch) and Development. Deployment Protection with Vercel Authentication, the automation bypass and shareable links works on Hobby; Password Protection needs Pro and costs $20 per project per month. The Neon native integration (billed through Vercel) can create a `preview/<git-branch>` database branch for preview deployments and injects DATABASE_URL (pooled) and DATABASE_URL_UNPOOLED. Hobby is restricted to non-commercial personal use. Pro is $20/month, which covers one deploying seat and $20 of usage credit; extra deploying seats are $20/month each. Pro functions are billed on active CPU (from $0.128/hr), provisioned memory (from $0.0106/GB-hr) and invocations ($0.60 per 1M). AI Gateway is an OpenAI-compatible endpoint at https://ai-gateway.vercel.sh/v1 with zero markup on token prices, and Pydantic AI has a built-in `VercelProvider` (`vercel:` prefix). Vercel's MCP server is https://mcp.vercel.com, a remote server that uses OAuth and only accepts approved clients; Claude Code and VS Code are on that list.

### Findings

- **Zero-config FastAPI detection: Vercel loads a top-level variable named `app` from app.py, index.py, server.py, main.py, wsgi.py or asgi.py, at the root or inside src/ or app/. A custom module can be set with `[tool.vercel] entrypoint = "module:variable"` in pyproject.toml. The older `[project.scripts] app = ...` form still works but is legacy.** [high, load-bearing]
  The FastAPI page lists the same entrypoints: https://vercel.com/docs/frameworks/backend/fastapi. A Vercel knowledge-base guide (https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel) also lists `api/` as a detected directory, but the reference docs do not. Rely on root, src/ or app/. A Build Command can go in `[tool.vercel.scripts] build = "..."`. Vercel CLI 48.1.8 or later is needed for `vercel dev` and `vc deploy` with FastAPI.
  Source: <https://vercel.com/docs/functions/runtimes/python>
- **Supported Python versions are 3.12 (default), 3.13 and 3.14. The version is set through `requires-python` in pyproject.toml, a `.python-version` file, or Pipfile.lock. If the version is missing or unsupported, Vercel falls back to 3.12.** [high, load-bearing]
  Source: <https://vercel.com/docs/functions/runtimes/python/python-version>
- **Dependencies can be declared in pyproject.toml (with or without uv.lock), requirements.txt, or Pipfile plus Pipfile.lock. uv has been the default installer for all Python builds since Oct 3, 2025.** [high, load-bearing]
  The uv changelog is at https://vercel.com/changelog/python-package-manager-uv-is-now-available-for-builds-with-zero and says builds are 30-65% faster. Python bundles are not tree-shaken: every reachable file is included. Python sources are precompiled to .pyc when space allows, which helps cold starts.
  Source: <https://vercel.com/docs/functions/runtimes/python>
- **Function limits with Fluid compute. Hobby: 300s default and maximum duration, 2 GB / 1 vCPU memory. Pro: 300s default, up to 800s (generally available), 1800s in beta (configured per function), and up to 4 GB / 2 vCPU. Python bundles can be 500 MB uncompressed, or up to 5 GB with Large Functions (beta). Request and response bodies are capped at 4.5 MB. Functions run in iad1 by default.** [high, load-bearing]
  Fluid compute plan defaults are at https://vercel.com/docs/fluid-compute. Durations above 800s need function-level `maxDuration`. A function that runs past its limit returns 504 FUNCTION_INVOCATION_TIMEOUT. Streamed responses count toward the duration.
  Source: <https://vercel.com/docs/functions/limitations>
- **Fluid compute has been on by default for new projects since April 23, 2025, and supports Python. With optimized concurrency, several requests share one instance, which suits I/O-bound LLM and database calls. Cold starts are reduced by pre-warming on production deployments and by bytecode optimization.** [high]
  The bytecode caching section on that page covers only Node.js 20+. Python precompiles .pyc at build time instead (see the Python runtime page). FastAPI lifespan events are supported, but shutdown cleanup gets at most 500ms after SIGTERM: https://vercel.com/docs/frameworks/backend/fastapi
  Source: <https://vercel.com/docs/fluid-compute>
- **Streaming is supported and on by default for Python functions. FastAPI `StreamingResponse` works for chunked text, SSE and LLM token streams.** [high]
  Also covered at https://vercel.com/docs/functions/streaming-functions (section 'Streaming Python functions'). The SSE example in the guide uses `media_type="text/plain"`; for SSE use `text/event-stream`. That is standard practice, not taken from Vercel's docs.
  Source: <https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel>
- **Running background work after the response is only documented for JS/TS (`waitUntil` from @vercel/functions, or `after()` in Next.js). The Python `vercel` package documents get_env, geolocation, ip_address and RuntimeCache, but no wait_until. Whether FastAPI BackgroundTasks finish reliably on Vercel is undocumented.** [low]
  Fluid compute advertises waitUntil (https://vercel.com/docs/fluid-compute), but none of the pages I read show a Python equivalent. For durable background jobs, Vercel points to Queues, Workflows, and Celery or Dramatiq on Vercel Queues (https://vercel.com/docs/frameworks/backend/celery).
  Source: <https://vercel.com/docs/functions/functions-api-reference/vercel-sdk-python>
- **Cron jobs go in the vercel.json `crons` array as `path` plus `schedule`. They only run on production deployments, in UTC, with no retries and best-effort delivery. Every plan allows 100 cron jobs per project. Hobby crons can run at most once per day and may fire anywhere within the scheduled hour (±59 min); more frequent expressions fail the deploy. Pro allows once per minute with per-minute precision.** [high, load-bearing]
  Quickstart: https://vercel.com/docs/cron-jobs/quickstart. If a `CRON_SECRET` env var is set, Vercel sends it as `Authorization: Bearer <CRON_SECRET>`: https://vercel.com/docs/cron-jobs/manage-cron-jobs. Cron runs use the same duration limits as functions (300s on Hobby).
  Source: <https://vercel.com/docs/cron-jobs/usage-and-pricing>
- **The documented way to run a frontend and a FastAPI backend in one project is Services: a top-level `services` map, where each entry has `root` and optionally `entrypoint`, `framework`, `runtime` and so on, plus top-level `rewrites` whose destination is `{ "service": "name" }`. Services are labelled Beta on all plans.** [high, load-bearing]
  A service gets no public traffic unless a rewrite points to it. The service receives the original path, so `/api/users` arrives as `/api/users` and FastAPI routes must include the `/api` prefix. When `services` is present, `functions`, `buildCommand`, `installCommand`, `outputDirectory` and `framework` must move inside each service. `vercel dev` runs all services locally. Services are billed like functions; service-to-service calls through bindings count as 'service requests' (Hobby includes 1M): https://vercel.com/docs/services/pricing. Routing details: https://vercel.com/docs/services/routing.
  Source: <https://vercel.com/docs/services>
- **The `experimentalServices` key (each service has `entrypoint` and `routePrefix`, and the project framework must be set to 'Services') is the earlier model. New projects should use `services` instead; experimentalServices stays available while you migrate.** [high, load-bearing]
  experimentalServices injected `{SERVICENAME}_URL` and `NEXT_PUBLIC_{SERVICENAME}_URL` env vars. Do not combine the old and new key shapes.
  Source: <https://vercel.com/docs/services/experimental>
- **There are two options that avoid the beta. (a) FastAPI serves a pre-built static frontend with `app.frontend("/", directory="dist")` or `app.mount(... StaticFiles ...)`; Vercel moves those files to the CDN at build time, and API routes take priority over the frontend. (b) Python files in `/api` are still supported for existing projects, but new apps should use the FastAPI preset or Services.** [high]
  The /api directory page is https://vercel.com/docs/functions/runtimes/python/api-directory. The `public/` directory is also served from the CDN at the root path. Files are kept in the function instead of the CDN when top-level middleware or Depends() guards exist, unless `[tool.vercel.fastapi.static] cdn = true` is set.
  Source: <https://vercel.com/docs/frameworks/backend/fastapi>
- **A preview deployment is created for every push to a non-production branch, every PR on GitHub, GitLab or Bitbucket, and every `vercel` CLI deploy without --prod. Each branch gets a URL that tracks its latest commit, and each commit gets its own URL. A new project's first deployment is always production. Custom environments such as 'staging' need Pro.** [high]
  Source: <https://vercel.com/docs/deployments/environments>
- **Each env var targets Production, Preview, Development and/or a custom environment (Pro). A Preview var can apply to all non-production branches or to one branch, and branch-specific values override. Variables are either Config or Secret (Secret values are write-only). The total size limit is 64 KB per deployment. Changes only apply to new deployments. `vercel env pull` writes them to a local .env file.** [high]
  Source: <https://vercel.com/docs/environment-variables>
- **Deployment Protection: Standard Protection (every URL except production domains) and All Deployments are available on every plan, as are Vercel Authentication, Shareable Links and Protection Bypass for Automation (`x-vercel-protection-bypass` header, or the `VERCEL_AUTOMATION_BYPASS_SECRET` system env var). Password Protection costs $20 per protected project per month on Pro and is not available on Hobby. Trusted IPs and Passport are Enterprise-only.** [high, load-bearing]
  Hobby's Deployment Protection row is at https://vercel.com/docs/plans/hobby. Bypass availability: https://vercel.com/docs/deployment-protection/methods-to-bypass-deployment-protection/protection-bypass-automation
  Source: <https://vercel.com/docs/deployment-protection>
- **Custom domains are added under Project > Settings > Domains > Add Domain. An apex domain uses an A record (Vercel shows the IP; 76.76.21.21 or the value on your domain card). A subdomain uses a project-specific CNAME such as `d1d4fc829fe7bc7c.vercel-dns-017.com`. Alternatively, switch to Vercel nameservers, which wildcard domains require. A domain already used by another Vercel account needs a TXT record for verification. IPv6/AAAA is not supported. Hobby allows 50 domains per project.** [high, load-bearing]
  The A-record IP comes from https://vercel.com/docs/domains/troubleshooting (a related-link mention). Always copy the values the dashboard shows for your project. If CAA records exist, they must allow letsencrypt.org.
  Source: <https://vercel.com/docs/domains/working-with-domains/add-a-domain>
- **The Neon integration comes in two forms. The Vercel-Managed (native, billed through Vercel) integration has opt-in Preview Branching under Advanced Options > Deployments Configuration > Preview, with 'Resource must be active before deployment' turned on. Each preview deployment then gets a Neon branch named `preview/<git-branch>`, and connection vars are injected for that deployment only. The vars are DATABASE_URL (pooled through PgBouncer), DATABASE_URL_UNPOOLED, PGHOST, PGHOST_UNPOOLED, PGUSER, PGDATABASE, PGPASSWORD and legacy POSTGRES_*.** [high, load-bearing]
  Preview-branch vars do not appear in Vercel's env var settings. Branches are deleted only when the matching deployments are removed, and preview deployments are retained for 6 months by default, so unused branches can pile up. The Neon-Managed (connectable account) integration also supports preview branching and cleans up when the Git branch is deleted: https://neon.com/docs/guides/vercel-overview. The two integrations cannot be combined in one project, and the native integration does not support `neon login`. Neon now brands itself 'Lakebase Postgres'.
  Source: <https://neon.com/docs/guides/vercel-managed-integration>
- **The Hobby plan is free and limited to non-commercial personal use. Commercial use covers any form of payment from visitors, advertising a product or service sale, being paid to build or host the site, affiliate-driven sites, and ads. Donations are allowed. Hobby users cannot buy extra usage; if you exceed a limit, the feature pauses until 30 days have passed.** [high, load-bearing]
  Hobby includes 4 CPU-hrs of active CPU, 360 GB-hrs of provisioned memory, 1M invocations, 100 GB Fast Data Transfer and 1M CDN requests: https://vercel.com/docs/plans/hobby. The pricing page FAQ states 'Our Hobby plan is for personal, non-commercial use.' (https://vercel.com/pricing).
  Source: <https://vercel.com/docs/limits/fair-use-guidelines>
- **Pro costs a $20/month platform fee. That fee includes 1 deploying seat and $20/month of usage credit, which expires monthly and applies to all managed-infrastructure usage from the first unit. Each extra Owner or Member seat costs $20/month; Viewer seats are free. Pro also includes a Flat Rate CDN tier (1M requests and 1 TB transfer) and a default $200 spend-management notification threshold.** [high, load-bearing]
  https://vercel.com/pricing shows Pro at $20/mo, $20 per developer seat, and 'a $20 included credit'. The pricing page lists 10M CDN requests and 1 TB for Pro, while the Pro plan docs say 1M requests and 1 TB under Flat Rate CDN. Treat the request count as unverified.
  Source: <https://vercel.com/docs/plans/pro-plan>
- **Functions are billed on Active CPU (only while code is executing; I/O waits are free), Provisioned Memory (GB-hours for the instance's lifetime, including I/O waits) and Invocations ($0.60 per 1M on Pro). Example rates: iad1 $0.128 per CPU-hr and $0.0106 per GB-hr; fra1 $0.184 and $0.0152.** [high, load-bearing]
  On Pro there are no separately included function quotas. Usage is drawn from the $20 credit and then billed on demand.
  Source: <https://vercel.com/docs/functions/usage-and-pricing>
- **AI Gateway is available on all plans. It exposes an OpenAI Chat Completions-compatible API (including /embeddings) at https://ai-gateway.vercel.sh/v1, authenticated with an AI Gateway API key or a Vercel OIDC token. It adds zero markup to provider list prices, including with BYOK. The free tier is a monthly credit restricted to a subset of models, has lower per-model rate limits, and requires a payment method on file. Buying credits moves you to the paid tier, which drops the free monthly credit. BYOK needs purchased credits.** [high, load-bearing]
  Base URL: https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-chat-completions. FAQ and payment-method requirement: https://vercel.com/docs/ai-gateway/faq. The free credit's dollar amount is not stated in the docs I read (low confidence on the amount). Optional add-ons cost extra, for example a team-wide ZDR setting on Pro at $0.10 per 1K requests.
  Source: <https://vercel.com/docs/ai-gateway/pricing>
- **Pydantic AI has a built-in VercelProvider (an OpenAI-compatible provider with base_url https://ai-gateway.vercel.sh/v1). Use it as `Agent('vercel:anthropic/claude-sonnet-4-5')` or `OpenAIChatModel(..., provider=VercelProvider(api_key=...))`. It reads the env var VERCEL_AI_GATEWAY_API_KEY, falling back to VERCEL_OIDC_TOKEN. Vercel's own docs name the variable AI_GATEWAY_API_KEY.** [high, load-bearing]
  Docs: https://github.com/pydantic/pydantic-ai/blob/main/docs/models/compatible-apis.md (section 'Vercel AI Gateway'). It needs the `openai` extra (`pydantic-ai-slim[openai]`). Inside Vercel Functions, the OIDC token is delivered in the `x-vercel-oidc-token` request header and is reused for up to 90 minutes. VERCEL_OIDC_TOKEN as an env var is documented only for builds and local `vercel env pull`, where it lasts 12 hours (https://vercel.com/docs/oidc). Relying on the env-var OIDC path at runtime is therefore risky; use an API key.
  Source: <https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/providers/vercel.py>
- **The Vercel MCP server is the remote endpoint https://mcp.vercel.com. It uses OAuth and Streamable HTTP and is available on all plans, but only approved clients can connect; the list includes Claude Code, Claude.ai/Desktop, VS Code with Copilot and Cursor. For Claude Code: `claude mcp add --transport http vercel https://mcp.vercel.com`, then authenticate through `/mcp`. Its tools cover doc search, project and deployment management, deployment logs and Web Analytics queries. A connection has the same access as your Vercel user account.** [high, load-bearing]
  Source: <https://vercel.com/docs/agent-resources/vercel-mcp>

### Exact snippets (copied from the sources named)

**pyproject.toml custom FastAPI entrypoint** — <https://vercel.com/docs/frameworks/backend/fastapi>

```toml
[tool.vercel]
entrypoint = "backend.server:app"
```

**pyproject.toml Python version + deps (Vercel example)** — <https://vercel.com/docs/functions/runtimes/python>

```toml
[project]
name = "my-python-api"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.117.1",
]
```

**vercel.json Services: frontend + FastAPI in one project (BETA)** — <https://vercel.com/docs/services>

```json
{
  "services": {
    "my_frontend": {
      "root": "frontend/"
    },
    "my_backend": {
      "root": "backend/",
      "entrypoint": "main:app"
    }
  },
  "rewrites": [
    { "source": "/api/(.*)", "destination": { "service": "my_backend" } },
    { "source": "/(.*)", "destination": { "service": "my_frontend" } }
  ]
}
```

**vercel.json maxDuration for FastAPI function (keyed by resolved entrypoint)** — <https://vercel.com/docs/frameworks/backend/fastapi>

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "app/main.py": {
      "maxDuration": 60
    }
  }
}
```

**vercel.json excludeFiles to keep Python bundle under 500 MB** — <https://vercel.com/docs/functions/runtimes/python>

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "app.py": {
      "excludeFiles": "{tests/**,__tests__/**,**/*.test.py,**/test_*.py,fixtures/**,__fixtures__/**,testdata/**,sample-data/**,static/**,assets/**}"
    }
  }
}
```

**vercel.json cron for a FastAPI route (production only; Hobby = max once/day)** — <https://vercel.com/kb/guide/ship-a-fastapi-app-on-vercel>

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "crons": [{ "path": "/api/cron/cleanup", "schedule": "0 0 * * *" }]
}
```

**Pydantic AI with Vercel AI Gateway (env: VERCEL_AI_GATEWAY_API_KEY)** — <https://github.com/pydantic/pydantic-ai/blob/main/docs/models/compatible-apis.md>

```python
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.vercel import VercelProvider

model = OpenAIChatModel(
    'anthropic/claude-sonnet-4-5',
    provider=VercelProvider(api_key='your-vercel-ai-gateway-api-key'),
)
agent = Agent(model)
```

**Add Vercel MCP to Claude Code** — <https://vercel.com/docs/agent-resources/vercel-mcp>

```bash
claude mcp add --transport http vercel https://mcp.vercel.com
```

### Recommendations
- For release 1, pick between (a) one project with Services (beta), with a Next.js or Vite frontend at `/` and FastAPI at `/api/(.*)`, and (b) a single FastAPI app using the generally available preset that serves a pre-built static SPA with `app.frontend("/", directory="dist")`. Option (b) avoids beta features and is a good fit for a beginner. Two separate Vercel projects is the fallback if Services misbehaves.
- With Services, the backend sees the original path, so declare FastAPI routes with the `/api` prefix, for example `APIRouter(prefix="/api")`. Also move any `functions`, `buildCommand` or `framework` keys inside the service object, because they are not allowed at the top level in services mode.
- Use pyproject.toml plus uv.lock. Pin Python with `.python-version` (3.13) or `requires-python`. Depend on `pydantic-ai-slim[openai,...]` rather than full `pydantic-ai` so the 500 MB Python bundle stays small, and add `excludeFiles` for tests and fixtures.
- Keep the region aligned with the database. Functions run in iad1 (Washington D.C.) by default, so create the Neon database in a US-East region, or change the function region to match.
- Use the Vercel-Managed Neon integration with Preview Branching turned on, so each PR's preview gets a `preview/<branch>` database branch with DATABASE_URL injected. Run Alembic migrations in the build step. Delete old preview deployments, or use the Neon-Managed integration, so branches do not linger for 6 months.
- Run the scheduled docs re-sync (crawl, embed, upsert into pgvector) as a GitHub Actions scheduled workflow, not a Vercel cron. Hobby crons run at most once a day with ±59 min jitter, are capped at 300s, and never retry. If you do use a Vercel cron, protect it with CRON_SECRET.
- Do not rely on post-response background work in Python on Vercel, because no Python waitUntil is documented. Finish LLM grading inside the request, using streaming for long outputs, or move it to a queue or workflow.
- For tutor, quiz and grader agents, AI Gateway is a good fit: zero markup, one key, fallbacks and spend budgets. Use Pydantic AI's `vercel:` provider and set VERCEL_AI_GATEWAY_API_KEY (not AI_GATEWAY_API_KEY). Use an API key in production rather than the OIDC token env var. You could also call the Anthropic or OpenAI providers directly; Pydantic AI makes switching a one-line change.
- Leave Deployment Protection on Standard (free; Vercel Authentication on previews). Create a Protection Bypass for Automation secret so GitHub Actions E2E tests can reach preview URLs. Use Vercel's 'GitHub Actions + vercel build/deploy --prebuilt' pattern only if you want CI-controlled deploys; otherwise the Git integration already creates previews per PR.
- Build on Hobby, but plan to move to Pro ($20/mo, including $20 of usage credit) before adding payments, ads or any paid tier, because Hobby forbids commercial use.
- Add the Vercel MCP server to Claude Code and VS Code (https://mcp.vercel.com, OAuth) for the 'GitHub for the Claude Code era' track. Its doc search and deployment-log tools work well as a lesson demo, but point out that it carries your full account permissions.

### Risks
- Services is labelled Beta and replaced `experimentalServices` within the past year. The config shape could change again, and older templates and tutorials may show the deprecated `experimentalServices` and `routePrefix` form.
- Pydantic AI reads VERCEL_AI_GATEWAY_API_KEY, while Vercel's docs and dashboard name the variable AI_GATEWAY_API_KEY. If the project copies Vercel's name, the provider raises a UserError at startup.
- Inside Vercel Functions the OIDC token is delivered in a request header, not reliably as the VERCEL_OIDC_TOKEN env var. A VercelProvider that depends on that env var at runtime may fail or use an expired token.
- Hobby limits: 300s maximum duration, 2 GB memory, 4 CPU-hrs and 360 GB-hrs per month. When exceeded, usage pauses for up to 30 days because Hobby cannot buy more. Heavy embedding or re-sync jobs or a traffic spike could take the site offline.
- There is no documented Python waitUntil. If FastAPI BackgroundTasks or fire-and-forget asyncio tasks are cut off when the instance pauses, grading or logging work could be lost silently.
- Neon preview branches can stay around for up to 6 months, tied to deployment retention, and use storage. Their connection vars do not appear in the Vercel env settings, which can confuse debugging.
- The 4.5 MB request/response body limit affects any file uploads in hands-on tasks.
- The AI Gateway free tier only covers a subset of models, has lower rate limits (HTTP 429), and needs a card on file. The docs I read do not state the free credit amount.
- Vercel docs are inconsistent in places: the knowledge-base guide lists an `api/` entrypoint directory that the reference docs omit, and the pricing page and Pro docs give different CDN request counts for Pro. Check against the dashboard before writing these values into a spec.

### Open questions
- Can top-level vercel.json `crons` target a path that rewrites into a Service? The Services docs do not say.
- Do FastAPI BackgroundTasks always run to completion after the response on Fluid compute? This needs a test on a preview deployment.
- What is the AI Gateway monthly free-credit amount now? It is not stated on the current pricing, FAQ or getting-started pages.
- Does the new `services` model need any dashboard framework-preset setting? The older experimentalServices model required the framework to be set to 'Services', and the new docs say nothing either way.
- Pro included CDN requests: 10M (pricing page) or 1M (Flat Rate CDN tier in the Pro docs)?
- Does the Neon native integration create one branch per Git branch (named preview/<git-branch>, reused) or one per deployment? The wording suggests per Git branch.
- Is VERCEL_OIDC_TOKEN set as a runtime env var for Python functions? The docs only describe the request header for functions.

### Fact-check (second agent re-read the sources)

Vercel docs were fetched as markdown by appending .md to each URL, and the primary sources were read on 2026-10-14. Three claims need correction. (1) The `vercel` Python package now has `vercel.functions.wait_until` (v0.10.0+, Aug 2026), though the vercel.com Python SDK docs page has not been updated to show it. (2) Wildcard domains can delegate `_acme-challenge` with NS records instead of switching to Vercel nameservers. (3) In the Pydantic AI claim, the statement that VERCEL_OIDC_TOKEN is 'only documented for builds and local' is wrong: AI Gateway docs say deployments receive it as an env var. Token TTLs are 1h for builds, 2h for functions (reused for up to 90 min) and 12h for development. Minor nuances: Hobby Shareable Links are limited to one link per account, and the research note's '10M CDN requests for Pro' is the paid $20/mo Flat Rate tier, not the included one. A Neon docs page contained an embedded 'note for AI assistants' asking for a POST to a feedback endpoint; it was ignored as page data.

Corrections:
- [corrected] Post-response background work is documented only for JS/TS. The Python `vercel` package has no wait_until. → The Vercel docs page for the Python SDK (vercel-sdk-python) still lists only get_env, geolocation, ip_address and RuntimeCache/AsyncRuntimeCache. However, the `vercel` PyPI package has exported `vercel.functions.wait_until(awaitable)` since v0.10.0 (Aug 12, 2026; added in PR #218 on Jul 31, 2026). It is in the current release, 0.11.6, and the package README documents it. It accepts awaitables only, is bounded by maxDuration, is not durable and is not retried. Separately, the Dramatiq guide exists at /docs/frameworks/backend/dramatiq; the Celery page does not mention Dramatiq. (<https://github.com/vercel/vercel-py/blob/main/src/vercel/functions/README.md>)
- [corrected] Custom domains: A record for an apex domain, project-specific CNAME for a subdomain, or Vercel nameservers 'which wildcard domains require'. TXT verification when another account uses the domain. No IPv6/AAAA. 50 domains per project on Hobby. → Wildcard domains no longer strictly require Vercel nameservers. If you cannot change nameservers, you can delegate `_acme-challenge` to ns1/ns2.vercel-dns.com with NS records and add a wildcard CNAME to cname.vercel-dns-0.com. Everything else is confirmed: the A record (76.76.21.21 or the domain card value, per the troubleshooting/KB link), the example CNAME d1d4fc829fe7bc7c.vercel-dns-017.com, TXT verification, the 'we do not support IPv6 yet' statement, the Hobby limit of 50 domains per project, and CAA records needing to allow letsencrypt.org. (<https://vercel.com/docs/domains/working-with-domains/add-a-domain>)
- [corrected] Pydantic AI VercelProvider: base_url https://ai-gateway.vercel.sh/v1, usable as 'vercel:anthropic/claude-sonnet-4-5' or OpenAIChatModel(..., provider=VercelProvider(api_key=...)). It reads VERCEL_AI_GATEWAY_API_KEY and falls back to VERCEL_OIDC_TOKEN. Vercel names the variable AI_GATEWAY_API_KEY. → The core claim is confirmed against vercel.py and compatible-apis.md, including the need for pydantic-ai-slim[openai]. One supporting detail is wrong: the claim that 'VERCEL_OIDC_TOKEN env var is documented only for builds and local env pull'. The AI Gateway auth docs say 'Vercel deployments receive an OIDC token as VERCEL_OIDC_TOKEN' and show Python reading it from the environment. Token lifetimes per /docs/oidc/reference: build tokens expire after 1 hour, preview/production function tokens after 2 hours (reused for up to 90 minutes, delivered in the x-vercel-oidc-token header), and development tokens after 12 hours. Using an API key for long-running processes is still sensible. (<https://vercel.com/docs/ai-gateway/authentication-and-byok>)

Snippet checks:
- pyproject.toml custom FastAPI entrypoint: none. It matches the FastAPI docs exactly.
- pyproject.toml Python version + deps: none. It matches the Python runtime docs exactly.
- vercel.json Services: none. It matches the /docs/services quick start exactly. Note that top-level functions/buildCommand/framework keys are invalid when `services` is present.
- vercel.json maxDuration keyed by app/main.py: none. It matches the FastAPI docs.
- vercel.json excludeFiles: none. It matches the Python runtime docs exactly.
- vercel.json cron: none. It matches the KB guide exactly. The route must accept GET, because Vercel invokes crons with HTTP GET.
- Pydantic AI VercelProvider snippet: none. It matches compatible-apis.md exactly.
- claude mcp add command: none. It matches the Vercel MCP docs exactly.
