# Neon (Lakebase Postgres) research

_Research archive. Checked against primary sources on 2026-10-14. Facts about fast-moving tools (Claude Code, Pydantic AI, FastAPI, GitHub, OpenRouter) go stale quickly: re-check before relying on a number._

- **Needed by:** Phase 2
- **Licence / attribution notes:** Neon docs cited by link. Note: Neon doc pages end with a note addressed to AI assistants asking for a feedback POST; it was treated as page data and ignored.
- **Covers:** plans and prices, pgvector versions and limits, Lakebase Search, pooling, Vercel integrations, branch actions, auth, AI gateway, MCP

## Neon (Lakebase Postgres, from Databricks) for a FastAPI + Pydantic AI learning site: pgvector/hybrid search, plans and cost, preview branching, Python serverless connections, Auth/AI Gateway/Functions/MCP, migrations

**Summary.** Neon now describes itself as a backend platform "from Databricks" built around Lakebase Postgres. Alongside the database it offers Managed Better Auth, a Data API, Functions, Object Storage and an AI Gateway. There are three plans (Free, Launch, Scale) and no monthly minimum. Launch costs $0.106/CU-hour and Scale $0.222/CU-hour. Storage is $0.35/GB-month and instant restore is $0.20/GB-month. Free gives each project 100 CU-hours/month, 1 GB of storage (20 GB per account), 10 branches, a 6-hour restore window and a fixed 5-minute scale-to-zero. For a 1-2 GB, low-traffic app with a few preview branches on Launch, my rough estimate is $3-10/month (0.25 CU active about 3 h/day is about 23 CU-h, or $2.40; 2 GB is $0.70; previews about $1; restore history costs cents). Keeping 0.25 CU always on costs about $19/month. Free only works if all branches together stay under 1 GB. pgvector is 0.8.0 on PG14-17 and 0.8.6 on PG18. HNSW indexes take up to 2,000 dimensions for vector and 4,000 for halfvec. pg_search (BM25) is unavailable; Neon now points to its own Lakebase Search extensions (lakebase_ann, lakebase_bm25), which need PG16+. Plain tsvector/GIN with a SQL reciprocal-rank-fusion query still works on any version. Both Vercel integrations (Vercel-Managed native and Neon-Managed connectable account) create a `preview/<git-branch>` branch for each preview deployment and inject DATABASE_URL (pooled) and DATABASE_URL_UNPOOLED; they differ in billing and in when old branches are cleaned up. The current GitHub Actions are create-branch-action@v6 (node24, supports expires_at and schema-only), delete-branch-action@v3, schema-diff-action@v1 (still declares node20) and reset-branch-action@v1; a branch TTL can be at most 30 days. For Python, Neon recommends psycopg 3 with the pooled URL (PgBouncer in transaction mode) at runtime and the direct URL for Alembic. Managed Better Auth does not yet support a separate frontend and backend. The AI Gateway is OpenAI-compatible but needs a paid plan plus prepaid credits. Neon Functions run Node.js only, so they don't fit this stack. The hosted MCP server is https://mcp.neon.tech/mcp, with OAuth or API-key auth and a ?readonly=true mode.

### Findings

- **Neon now describes itself as a set of cloud backend primitives 'built around Lakebase Postgres ... from Databricks': Lakebase Postgres, Managed Better Auth, Data API, Functions, Object Storage and AI Gateway. Docs call the database 'Lakebase Postgres' throughout.** [high]
  The pricing page says 'from Databricks'. Third-party coverage puts the Databricks deal close around June 2025. Product names in lessons and specs should say 'Lakebase Postgres on Neon'.
  Source: <https://neon.com/docs/llms.txt>
- **Plans are Free, Launch and Scale. Launch and Scale are pay-as-you-go, metered hourly, with no monthly minimum. Compute is $0.106/CU-hour on Launch and $0.222/CU-hour on Scale. Storage is $0.35/GB-month and instant restore $0.20/GB-month on both. Invoices under $0.50 are not collected.** [high, load-bearing]
  Same figures at https://neon.com/docs/introduction/plans. Public egress: 500 GB/project included on paid plans, then $0.10/GB. 1 CU is about 4 GB RAM; 0.25 CU for 4 h = 1 CU-hour. Every compute counts toward usage, including each branch's read-write compute.
  Source: <https://neon.com/pricing>
- **Free plan: 100 CU-hours per project per month, 1 GB storage per project (20 GB per account), 10 branches per project with no extra branches, autoscaling up to 2 CU, scale-to-zero after 5 min (cannot be disabled), 6-hour history window (capped at 1 GB), 5 GB egress per project, 100 projects.** [high, load-bearing]
  100 CU-hours is enough for a 0.25 CU compute running 400 h/month. The 1 GB storage limit covers all branches in the project combined.
  Source: <https://neon.com/docs/introduction/plans>
- **Paid branching and restore: Launch includes 10 branches per project and Scale 25. Extra branches cost $1.50/branch-month, prorated hourly, up to 5,000 per project. History window is up to 7 days on Launch and 30 days on Scale; the default is 1 day on paid plans and 6 hours on Free. Restore history is charged only on root branches.** [high, load-bearing]
  A child branch starts at zero storage and is billed on the smaller of its accumulated changes or its logical size. Launch scale-to-zero is 5 min and can be disabled (the latency doc says it can be extended to 7 days). Scale allows 1 min to always-on. Branches idle for 24 h and older than 14 days are archived automatically.
  Source: <https://neon.com/docs/introduction/plans>
- **pgvector is available on every Neon plan with no add-on. The version is 0.8.0 on PG14, 15, 16 and 17, and 0.8.6 on PG18. Install with CREATE EXTENSION vector, once per database.** [high, load-bearing]
  The pgvector page (https://neon.com/docs/extensions/pgvector) says you can install the latest supported version or the one before it. Neon supports PG 14-18 (https://neon.com/docs/postgresql/postgres-version-policy). The default major version for new projects was not stated.
  Source: <https://neon.com/docs/extensions/pg-extensions>
- **HNSW (and IVFFlat) dimension limits: vector up to 2,000, halfvec up to 4,000, bit up to 64,000, sparsevec up to 1,000 non-zero elements.** [high, load-bearing]
  1536-dim embeddings (e.g. OpenAI text-embedding-3-small) fit an HNSW index on the vector type. 3072-dim embeddings need halfvec (halfvec_cosine_ops). HNSW indexes can be created on an empty table; IVFFlat needs data first.
  Source: <https://neon.com/docs/extensions/pgvector>
- **Neon's index-build guidance: create indexes after loading data. maintenance_work_mem defaults by compute size; set it to roughly the working-set size but no more than 50-60% of compute RAM (10 GB was tested on a 7 CU/28 GB compute). max_parallel_maintenance_workers defaults to 2. hnsw.ef_search defaults to 40. Progress is visible in pg_stat_progress_create_index.** [high]
  The page shows `SET LOCAL hnsw.ef_search = 100;`. Use SET LOCAL inside a transaction, because a plain session SET does not stick on pooled (PgBouncer transaction-mode) connections.
  Source: <https://neon.com/docs/extensions/pgvector>
- **pg_search (ParadeDB BM25) is unavailable on every Postgres version and its library is marked deprecated; pgrag is also deprecated. Neon's replacement is Lakebase Search: lakebase_vector (lakebase_ann index, IVF + RaBitQ), lakebase_text (lakebase_bm25 index on standard tsvector) and lakebase_tokenizer. These are on PG16-18 only.** [high, load-bearing]
  Get-started (https://neon.com/docs/ai/lakebase-search-get-started) says PG16+ is required and there is no built-in hybrid function; it shows a hand-written reciprocal rank fusion query (k=60, top 40 from each side). lakebase_vector depends on pgvector (CASCADE installs it) and keeps pgvector types and operators. Build the BM25 index after inserting data. BM25 scores are negative: lower means more relevant. Plain Postgres full-text search (tsvector + GIN + ts_rank) still works on any version; pg_trgm 1.6 is on all versions and rum 1.3 on PG14-17 only. Plan or region limits for Lakebase Search are not stated.
  Source: <https://neon.com/docs/ai/lakebase-search>
- **Neon pooling is PgBouncer in transaction mode, reached through the '-pooler' hostname. It accepts up to 10,000 client connections, with default_pool_size = 0.9 × max_connections. Pooled connections do not support SET/RESET, SQL-level PREPARE/DEALLOCATE, session advisory locks or temp tables. Protocol-level prepared statements are supported (max_prepared_statements=1000). Neon says to use the direct URL for migrations, pg_dump, logical replication and admin work.** [high, load-bearing]
  The pooled form is postgresql://user:pass@ep-xxx-pooler.<region>.aws.neon.tech/neondb?sslmode=require&channel_binding=require (https://neon.com/docs/connect/choose-connection). The choose-connection page warns against double pooling: with a pooled Neon URL, avoid a client-side pool, or release connections promptly.
  Source: <https://neon.com/docs/connect/connection-pooling>
- **For Python, Neon recommends psycopg 3 for new projects ('psycopg[binary]'). With SQLAlchemy, use 2.0.33 or later (older versions reuse idle connections after scale-to-zero) and set pool_pre_ping=True or pool_recycle at or below the scale-to-zero timeout.** [high]
  SQLAlchemy notes: https://neon.com/docs/guides/sqlalchemy. The asyncpg examples in the Python guide just call asyncpg.connect(conn_string) and give no guidance on PgBouncer.
  Source: <https://neon.com/docs/guides/python>
- **Prepared statements behind PgBouncer: psycopg 3.2+ supports them with PgBouncer 1.22 or newer, max_prepared_statements > 0, and a client libpq from PostgreSQL 17 or newer. psycopg binary wheels have bundled libpq 17 on Linux and macOS since 3.2.3/3.2.4; the current release is 3.3.6. asyncpg's FAQ still says to pass statement_cache_size=0 under transaction-mode PgBouncer.** [medium, load-bearing]
  Wheel and libpq details: https://www.psycopg.org/psycopg3/docs/news.html. asyncpg: https://magicstack.github.io/asyncpg/current/faq.html. Neon's PgBouncer setup meets psycopg's conditions on paper, but I did not test it on Neon. If you see 'prepared statement does not exist' errors, set prepare_threshold=None (psycopg) or statement_cache_size=0 (asyncpg).
  Source: <https://www.psycopg.org/psycopg3/docs/advanced/prepare.html>
- **Cold starts after scale-to-zero typically add 'a few hundred milliseconds'. Neon suggests longer connect timeouts (e.g. connect_timeout=10-15), retries with backoff, same-region placement, and sslnegotiation=direct (needs a PG17+ client library) to shorten the TLS handshake.** [high]
  Neon's Vercel advice is for JavaScript only: node-postgres plus attachDatabasePool from @vercel/functions on Fluid compute (https://neon.com/docs/guides/vercel-connection-methods). I found no Python-specific Vercel guidance, so the Python setup has to be inferred: pooled URL, small or no client pool, short idle timeouts.
  Source: <https://neon.com/docs/connect/connection-latency>
- **Vercel integrations: Vercel-Managed (Marketplace > Native Integrations > 'Neon Postgres', billed through Vercel) and Neon-Managed (Marketplace > Connectable Accounts > 'Neon', billed through Neon, for existing Neon accounts). Both create a Neon branch named preview/<git-branch> for each preview deployment and inject DATABASE_URL (pooled), DATABASE_URL_UNPOOLED and legacy PG*/POSTGRES_* variables. A manual connection is for custom CI/CD such as GitHub Actions.** [high, load-bearing]
  Vercel-Managed: preview variables arrive by webhook at deployment time and cannot be viewed in Vercel settings; preview branches are deleted only when Vercel deletes the deployment (default retention 6 months; projects with fewer than ~20 previews may never auto-delete) (https://neon.com/docs/guides/vercel-managed-integration, https://neon.com/docs/guides/vercel-branch-cleanup). Neon-Managed: optional persistent vercel-dev branch; cleanup when the Git branch is deleted, run at the next preview deployment; the two integrations cannot coexist in one Vercel project, and one Neon project maps to one Vercel project; renaming branches breaks cleanup (https://neon.com/docs/guides/neon-managed-vercel-integration). Neon's example puts migrations in the Vercel build command override.
  Source: <https://neon.com/docs/guides/vercel-overview>
- **Current Neon GitHub Actions: create-branch-action@v6 (latest release '6.3.1' on 2026-03-31; tag v6.4.0 also exists; runs on node24). delete-branch-action@v3 (v3.2.1, composite, installs neonctl; the 'branch' input takes a name or ID and branch_id is deprecated). schema-diff-action@v1 (v1.0.1; action.yml still declares node20; needs pull-requests: write). reset-branch-action@v1 (v1.3.2).** [high, load-bearing]
  Checked with gh api on releases, tags and action.yml for each repo: https://github.com/neondatabase/delete-branch-action, https://github.com/neondatabase/schema-diff-action, https://github.com/neondatabase/reset-branch-action. Setup needs a NEON_API_KEY secret and a NEON_PROJECT_ID variable; the Neon GitHub integration can create both (https://neon.com/docs/guides/branching-github-actions).
  Source: <https://github.com/neondatabase/create-branch-action>
- **create-branch-action inputs: api_key, project_id, branch_name, parent_branch, database (default neondb), role (default neondb_owner), branch_type ('default' or 'schema-only'), ssl, suspend_timeout (default '0'), expires_at (RFC 3339), masking_rules, get_auth_url, get_data_api_url. Outputs: db_url, db_url_pooled, db_host, db_host_pooled, password, branch_id, created, auth_url, data_api_url.** [high, load-bearing]
  The README says 'Set to 0 to disable auto-suspend', but the Neon API defines suspend_timeout_seconds 0 as 'use the default value' (300 s) and -1 as never suspend (https://neon.com/api_spec/release/v2.json). The README example workflow also references `steps.create-branch.outputs.host`, which is not an output (use db_host), and `needs.setup.outputs.branch`, which needs a setup job.
  Source: <https://github.com/neondatabase/create-branch-action/blob/main/action.yml>
- **Branch expiration works as a TTL. Set it with expires_at (RFC 3339, second precision) through the API, --expires-at in the CLI, or the Console; the maximum is 30 days ahead. It cannot be set on protected, default or parent branches. The Console defaults to 1 day; the CLI and API have no default. Resetting from the parent restarts the TTL.** [high, load-bearing]
  Suggested lengths: CI 2-4 h, feature work 1-7 days. The Vercel integrations do not set expiration on preview branches.
  Source: <https://neon.com/docs/guides/branch-expiration>
- **Schema-only branches copy only the schema and are independent root branches. They count toward a root-branch allowance (Free 3, Launch 5, Scale 25 per project, including main), and each has a maximum size (Free 1 GB, Launch 3 GB, Scale 20 GB). They cannot be reset from the parent. Create them in the Console or API, or with create-branch-action branch_type: schema-only; the Neon CLI does not support them yet.** [high, load-bearing]
  As root branches they are billed on full size and are where instant-restore history is charged, unlike copy-on-write child branches.
  Source: <https://neon.com/docs/guides/branching-schema-only>
- **For Python migrations, Neon's guide pairs SQLAlchemy and Alembic with FastAPI ('alembic revision --autogenerate', 'alembic upgrade head') and says a direct (non-pooled) connection string is required. There is a separate Django migrations guide. The Neon MCP server offers branch-based prepare_database_migration and complete_database_migration tools, and schema-diff-action posts schema diffs on PRs.** [high, load-bearing]
  The guide sets sqlalchemy.url in alembic/env.py from DATABASE_URL and uses psycopg2-binary. On Vercel, point Alembic at DATABASE_URL_UNPOOLED. MCP migration tools: https://neon.com/docs/ai/neon-mcp-server.
  Source: <https://neon.com/docs/guides/sqlalchemy-migrations>
- **Managed Better Auth (the current 'Neon Auth', running Better Auth 1.7.6) keeps users and sessions in the neon_auth schema of your database, branches with it, and is auto-provisioned on Vercel preview branches. It is included up to 60k MAU on Free and 1M MAU on Launch and Scale, AWS regions only. SDKs cover JS/Next.js/React. 'Standalone frontend + backend' setups are listed as 'Coming soon' (not supported).** [high, load-bearing]
  Roadmap: https://neon.com/docs/auth/roadmap. Supported plugins include email/password, social OAuth (Google, GitHub, Vercel), email OTP, magic link, JWT, admin, and organization (partial); MFA is coming. Not supported with IP Allow or Private Networking. The Data API checks JWTs against JWKS. A FastAPI backend on a separate deployment would therefore fall into the currently unsupported case. Legacy Stack Auth-based Neon Auth still works and has a migration guide.
  Source: <https://neon.com/docs/auth/overview>
- **Neon AI Gateway is an LLM gateway built into each branch, serving Databricks-hosted models. It has an OpenAI-compatible /v1 (chat completions, embeddings, Responses) plus Anthropic Messages and Gemini dialects. It requires Launch or Scale and prepaid credits (1 credit = $1, $5 minimum, valid 12 months), with no markup over provider prices. It runs only in aws-us-east-1, aws-us-east-2, aws-eu-central-1 and aws-ap-southeast-1.** [high, load-bearing]
  Providers in the catalog: Anthropic, OpenAI, Google, Meta, Alibaba, Zhipu, Thinking Machines, Moonshot, xAI, DeepSeek. Embeddings: qwen3-embedding-0-6b (1024 dims, $0.02/M), gte-large-en, bge-large-en (https://neon.com/docs/ai-gateway/models). Limits: 200,000 TPM soft limit plus an unpublished account-level daily spend cap (429 REQUEST_LIMIT_EXCEEDED). Get a credential with `neon credentials create --scope ai_gateway:invoke`; the per-branch base URL looks like https://br-...-api.ai.<cell>.<region>.aws.neon.tech (https://neon.com/docs/ai-gateway/get-started). Some catalog models have released=false and should be hidden. Many model names are newer than my knowledge and I could not verify them independently.
  Source: <https://neon.com/docs/ai-gateway/overview>
- **Neon Functions are long-running serverless functions on a branch. They run only JavaScript/TypeScript on Node.js 24, with a 15-minute heartbeat timeout, 2048 MiB fixed memory and 100 concurrent invocations per account by default, in the same 4 AWS regions as the AI Gateway. Function Triggers add cron and object-upload events.** [high]
  Limits: https://neon.com/docs/compute/functions/reference/runtime-limits. Pricing on Launch: $0.10 active / $0.025 waiting per Capacity-Hour plus $0.60 per million invocations. Not relevant to a FastAPI/Pydantic AI (Python) backend; the scheduled docs re-sync fits GitHub Actions better.
  Source: <https://neon.com/docs/compute/functions/overview>
- **The Neon MCP server is hosted at https://mcp.neon.tech/mcp (Streamable HTTP) and authenticates with OAuth or an API key ('Authorization: Bearer <NEON_API_KEY>'). URL parameters add read-only mode (?readonly=true, also selectable during OAuth), project scoping (?projectId=...) and tool categories (?category=...). The local stdio package @neondatabase/mcp-server-neon is deprecated. Neon recommends MCP for development and testing only, never production.** [high, load-bearing]
  Claude Code setup: `npx add-mcp https://mcp.neon.tech/mcp -a claude-code` (OAuth) or `claude mcp add --transport http neon ...` with a Bearer header; `npx neon@latest init` installs the MCP server and agent skills together (https://neon.com/docs/ai/connect-mcp-clients-to-neon). It is also an official Claude connector. Tools can be listed without auth via https://mcp.neon.tech/api/list-tools?readonly=true.
  Source: <https://neon.com/docs/ai/neon-mcp-server>

### Exact snippets (copied from the sources named)

**pgvector enable + HNSW cosine index + per-transaction ef_search (lines copied from Neon pgvector doc)** — <https://neon.com/docs/extensions/pgvector>

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops);

CREATE INDEX ON items USING hnsw (embedding vector_l2_ops) WITH (m = 16, ef_construction = 64);

SET LOCAL hnsw.ef_search = 100;
```

**Lakebase Search setup (PG16+): extensions, table with generated tsvector, lakebase_ann index** — <https://neon.com/docs/ai/lakebase-search-get-started>

```sql
CREATE EXTENSION IF NOT EXISTS lakebase_vector CASCADE;
CREATE EXTENSION IF NOT EXISTS lakebase_text CASCADE;

CREATE TABLE documents (
  id        SERIAL PRIMARY KEY,
  title     TEXT NOT NULL,
  body      TEXT NOT NULL,
  embedding VECTOR(1024),
  body_tsv  TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', body)) STORED
);

CREATE INDEX documents_embedding_idx ON documents
  USING lakebase_ann (embedding vector_cosine_ops);
```

**Hybrid search via Reciprocal Rank Fusion (SQL body from Neon's TS example; ${...} are driver parameters)** — <https://neon.com/docs/ai/lakebase-search-get-started>

```sql
    WITH vector_ranked AS (
      SELECT id, RANK() OVER (ORDER BY dist) AS rank
      FROM (
        SELECT id, embedding <=> ${queryVector}::vector AS dist
        FROM documents ORDER BY dist LIMIT 40
      ) v
    ),
    keyword_ranked AS (
      SELECT id, RANK() OVER (ORDER BY score) AS rank
      FROM (
        SELECT id, body_tsv <@> to_bm25query(to_tsvector('english', ${query}), 'documents_bm25') AS score
        FROM documents ORDER BY score LIMIT 40
      ) k
    )
    SELECT d.id, d.title,
      COALESCE(1.0 / (60 + v.rank), 0) + COALESCE(1.0 / (60 + k.rank), 0) AS rrf_score
    FROM documents d
    LEFT JOIN vector_ranked v ON d.id = v.id
    LEFT JOIN keyword_ranked k ON d.id = k.id
    WHERE v.id IS NOT NULL OR k.id IS NOT NULL
    ORDER BY rrf_score DESC, d.id
    LIMIT ${limit}
```

**create-branch-action@v6 with 14-day expiry (README example, verbatim; note: outputs.host should be outputs.db_host, and needs.setup requires a 'setup' job)** — <https://github.com/neondatabase/create-branch-action>

```yaml
name: Neon Github Actions Create Branch

on:
  # You can modify the following line to trigger the workflow on a different event, such as `push` or `pull_request`, as per your requirements. We have used `workflow_dispatch` for triggering the action in this example.
  workflow_dispatch:

jobs:
  create-neon-branch:
    runs-on: ubuntu-24.04
    steps:
      - name: Get branch expiration date as an env variable (2 weeks from now)
        id: get-expiration-date
        run:
          echo "EXPIRES_AT=$(date -u --date '+14 days' +'%Y-%m-%dT%H:%M:%SZ')"
          >> "$GITHUB_ENV"
      - name: Create Neon Branch
        uses: neondatabase/create-branch-action@v6
        id: create-branch
        with:
          project_id: ${{ vars.NEON_PROJECT_ID }}
          branch_name:
            pr-${{ github.event.number }}-${{ needs.setup.outputs.branch }}
          api_key: ${{ secrets.NEON_API_KEY }}
          expires_at: ${{ env.EXPIRES_AT }}
      - run: echo db_url ${{ steps.create-branch.outputs.db_url }} # the password is masked when printed
      - run: echo host ${{ steps.create-branch.outputs.host }}
      - run: echo branch_id ${{ steps.create-branch.outputs.branch_id }}
      - run:
          psql ${{ steps.create-branch.outputs.db_url }} -c "SELECT * FROM
          NOW();"
```

**Delete Vercel preview branch on PR close (works with both Vercel integrations)** — <https://neon.com/docs/guides/vercel-branch-cleanup>

```yaml
name: Cleanup Neon preview branch
on:
  pull_request:
    types: [closed]
jobs:
  delete-branch:
    runs-on: ubuntu-latest
    steps:
      - uses: neondatabase/delete-branch-action@v3
        with:
          project_id: ${{ vars.NEON_PROJECT_ID }}
          branch: preview/${{ github.head_ref }}
          api_key: ${{ secrets.NEON_API_KEY }}
```

**schema-diff-action@v1 PR comment (README)** — <https://github.com/neondatabase/schema-diff-action>

```yaml
permissions:
  pull-requests: write
  contents: read
steps:
  - uses: neondatabase/schema-diff-action@v1
    with:
      project_id: rapid-haze-373089
      compare_branch: dev/sunny_plant
      api_key: ${{ secrets.NEON_API_KEY }}
```

**Neon MCP server in Claude Code (API key) and read-only URL** — <https://neon.com/docs/ai/connect-mcp-clients-to-neon>

```bash
claude mcp add --transport http neon https://mcp.neon.tech/mcp \
  --header "Authorization: Bearer <YOUR_NEON_API_KEY>"

# Read-only mode URL:
https://mcp.neon.tech/mcp?readonly=true
```

**Neon AI Gateway via OpenAI Python SDK (OpenAI-compatible base URL)** — <https://neon.com/docs/ai-gateway/get-started>

```python
from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()
client = OpenAI(
    api_key=os.environ["NEON_AI_GATEWAY_TOKEN"],
    base_url=f"{os.environ['NEON_AI_GATEWAY_BASE_URL']}/v1",
)
response = client.chat.completions.create(
    model="gpt-5-mini",
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

### Recommendations
- Start development on the Free plan. Move to Launch when total storage across all branches nears 1 GB, when you need more than 10 branches, more than 6 hours of restore history, or the AI Gateway. Launch has no monthly minimum, so expect about $3-10/month for this app.
- Create the project in AWS us-east-1 or us-east-2. That keeps it close to Vercel's default region (iad1) and inside the AI Gateway/Functions regions. Choose Postgres 17 or 18 explicitly: 16+ keeps Lakebase Search available and 18 has pgvector 0.8.6.
- For RAG in release 1, use pgvector HNSW (vector_cosine_ops) plus a generated tsvector column with a GIN index, combined with a SQL RRF query. It is portable, standard Postgres and good teaching material. Treat Lakebase Search (lakebase_ann/lakebase_bm25) as an optional Neon-only upgrade. Keep embeddings at or below 2,000 dims, or use halfvec up to 4,000.
- Make the scheduled docs re-sync incremental: hash chunks and upsert only changed rows. This avoids rewriting the whole corpus, which inflates WAL/restore-history charges and forces HNSW rebuilds on a small 0.25-1 CU compute. Raise maintenance_work_mem per session only for a full rebuild.
- Runtime database access: use psycopg 3 (psycopg[binary] >= 3.2.4) with the pooled DATABASE_URL. Open short-lived connections or use a very small pool so you are not pooling twice. Set connect_timeout of about 10-15 s for cold starts and use SET LOCAL for hnsw.ef_search. If you use SQLAlchemy, use 2.0.33+ with pool_pre_ping=True. If you use asyncpg, set statement_cache_size=0.
- Run Alembic only against DATABASE_URL_UNPOOLED (direct), either in the Vercel build command or in a GitHub Actions step before deploy.
- Use the Neon-Managed Vercel integration with 'Automatically delete obsolete Neon branches' enabled, plus delete-branch-action@v3 on PR close. That keeps billing in Neon and cleans up branches immediately, which protects the 10-branch Free/Launch allowance.
- For CI tests, use create-branch-action@v6 with expires_at of a few hours. Use branch_type: schema-only only if you need no data, and remember those branches count against the root-branch allowance (3 on Free). Do not copy the README's suspend_timeout claim: leave it unset or '0' (API default 300 s). Pin to @v6, @v3 and @v1, or to commit SHAs.
- Connect Neon MCP to Claude Code with OAuth and https://mcp.neon.tech/mcp?readonly=true&projectId=<id> for learning. Use write mode only against dev branches.
- Keep the LLM provider choice independent of Neon in release 1. The AI Gateway works with Pydantic AI's OpenAI-compatible provider via base_url and covers Claude, GPT and Gemini, but it requires a paid plan and prepaid credits and has an unpublished daily spend cap.
- Defer accounts. Managed Better Auth (free to 60k MAU) currently does not support a frontend and backend on separate deployments; check the roadmap again before release 2. Ignore Neon Functions, which are Node-only.

### Risks
- Free plan storage is 1 GB per project across all branches combined. Embeddings plus HNSW indexes, plus preview branches that diverge through re-syncs, can exceed it. Free cannot buy extra branches (10 per project, including main, vercel-dev and preview/*).
- Vercel-Managed preview branches can linger for months because cleanup follows Vercel's deployment retention (6-month default), and projects with fewer than ~20 previews may never auto-delete. Stale branches use branch slots and storage.
- PgBouncer transaction mode does not keep session state: a plain SET hnsw.ef_search, SET search_path, advisory locks and SQL PREPARE fail or silently do nothing on the pooled URL. Migrations through the pooler can fail.
- asyncpg's default prepared-statement cache can produce 'prepared statement "__asyncpg_stmt_xx__" does not exist' errors behind PgBouncer. psycopg 3 needs bundled libpq 17 (binary wheels from 3.2.4) for automatic prepared statements to be safe.
- Scale-to-zero cold starts add a few hundred ms to the first tutor request after 5 minutes idle, on top of Vercel function cold starts. Free cannot disable it, and an always-on 0.25 CU costs about $19/month on Launch.
- schema-diff-action@v1 still declares node20. GitHub removed Node 20 from hosted runners on 2026-09-23 (https://github.blog/changelog/2026-09-23-node-20-is-no-longer-available-in-github-actions/), and I could not confirm whether node20 actions now run on Node 24 without problems.
- The create-branch-action README has small errors: suspend_timeout '0' semantics, the outputs.host reference, and an undefined needs.setup. Copying the examples as-is into lesson material would mislead learners.
- Lakebase Search is Neon/Databricks-specific (lakebase_* extensions, PG16+). Building on it ties the RAG layer and lesson content to Neon, unlike standard pgvector + tsvector.
- The AI Gateway restricts access by Anthropic's supported-regions policy, needs prepaid credits, and its catalog includes models flagged released=false. Pricing and models change quickly.
- Both Vercel integrations cannot be installed on the same Vercel project, and a Neon project maps to exactly one Vercel project, so switching later requires disconnecting and reconfiguring environment variables.

### Open questions
- Which Postgres major version does Neon use by default for new projects? Not stated on the pages checked.
- Is Lakebase Search (lakebase_vector/lakebase_text) available on the Free plan and in every region? The docs list no plan restriction, only PG16+.
- Does schema-diff-action@v1, which declares node20, still run correctly now that GitHub-hosted runners use only Node 24?
- Are the injected preview DATABASE_URL_UNPOOLED values available during a Vercel Python build, so Alembic can run in the build command? Neon shows this only with a Prisma example.
- Does the Vercel-Managed (native) integration offer Neon's Free plan, and does it follow Neon's branch limits exactly?
- Once standalone frontend+backend support ships for Managed Better Auth, how will a FastAPI backend verify sessions or JWTs (JWKS URL, JWT plugin claims)?
- What is the actual AI Gateway account-level daily spend cap for a new Launch account? Neon does not publish it.
- Can Pydantic AI's OpenAI provider use the AI Gateway's Anthropic Messages endpoint directly, or only the OpenAI-compatible /v1 path? I did not test this.

### Fact-check (second agent re-read the sources)

I checked every claim against current primary sources: Neon docs fetched as .md, GitHub raw files, the GitHub API, PyPI, the psycopg and asyncpg docs, the Neon API spec, and the live mcp.neon.tech list-tools endpoint. Four claims are corrected; the other 12 are confirmed.

1. **Schema-only branches:** the Neon CLI does support them (`neon branches create --schema-only`). The schema-only page's own intro sentence is stale.
2. **AI Gateway:** the Responses API is at /openai/v1/responses, not under the unified /v1.
3. **pgvector limits:** the sparsevec limit applies to HNSW only, not IVFFlat.
4. **create-branch-action inputs:** the list is missing api_host and prisma.

Other caveats:
- The create-branch-action tag v6.4.0 points to an older node20 commit than v6 and 6.3.1, which share one node24 commit.
- The pooling doc lists only temp tables with ON COMMIT PRESERVE/DELETE ROWS as unsupported, not all temp tables.
- The AI Gateway models page contains a stray 'Inference is free during the private preview' line.

Every fetched Neon doc page ends with a 'Note for AI assistants' asking agents to POST feedback to feedback.neon.tech. I treated it as page content and did not act on it. All work was read-only, and downloads went to the session scratchpad only.

Corrections:
- [corrected] HNSW (and IVFFlat) dimension limits: vector up to 2,000, halfvec up to 4,000, bit up to 64,000, sparsevec up to 1,000 non-zero elements. → The HNSW limits are correct. IVFFlat shares the vector, halfvec and bit limits but does not list sparsevec at all, so the sparsevec limit (1,000 non-zero elements) applies to HNSW only. The other points are confirmed: an HNSW index can be built on an empty table, while IVFFlat needs data first. (<https://neon.com/docs/extensions/pgvector>)
- [corrected] create-branch-action inputs: api_key, project_id, branch_name, parent_branch, database (neondb), role (neondb_owner), branch_type, ssl, suspend_timeout ('0'), expires_at, masking_rules, get_auth_url, get_data_api_url. Outputs: db_url, db_url_pooled, db_host, db_host_pooled, password, branch_id, created, auth_url, data_api_url. → The outputs are exact. The input list is missing two inputs: api_host (default https://console.neon.tech/api/v2) and prisma (default 'false'). The other inputs and defaults are correct. The suspend_timeout point holds: the action passes the value as suspend_timeout_seconds, and the API spec says 0 means 'use the default value' (300 s) while -1 means never suspend. The README's 'Set to 0 to disable auto-suspend' is therefore wrong. The README example's outputs.host and needs.setup problems are also confirmed. (<https://github.com/neondatabase/create-branch-action/blob/main/action.yml>)
- [corrected] Schema-only branches are independent root branches; root-branch allowance Free 3 / Launch 5 / Scale 25 (incl. main); max size Free 1 GB / Launch 3 GB / Scale 20 GB; no reset from parent; Console, API, or create-branch-action branch_type: schema-only; Neon CLI does not support them yet. → The CLI does support them: `neon branches create --schema-only` appears in the CLI reference, and the schema-only page has its own CLI section showing `neon branch create --schema-only`. That page's intro sentence ('Support for the Neon CLI will come in a future release') is stale and contradicts its own CLI section. The other points match https://neon.com/docs/guides/branching-schema-only. The feature is still labeled Beta. (<https://neon.com/docs/cli/branches>)
- [corrected] Neon AI Gateway is built into each branch, serving Databricks-hosted models; OpenAI-compatible /v1 (chat completions, embeddings, Responses) plus Anthropic Messages and Gemini dialects; requires Launch/Scale and prepaid credits (1 credit=$1, $5 min, 12 months), no markup; only aws-us-east-1, aws-us-east-2, aws-eu-central-1, aws-ap-southeast-1. → The Responses API is not under the unified /v1. It lives at /openai/v1/responses (native OpenAI dialect, also /ai-gateway/openai/v1/responses). The unified paths are /v1/chat/completions, /v1/embeddings and /v1/models. Anthropic uses /anthropic/v1/messages and Gemini /gemini/v1beta/models/{model}:generateContent. Confirmed: Databricks-hosted models, plans, credits, no markup, the 4 regions, the provider list, the embedding models (qwen3-embedding-0-6b 1024 dims at $0.02/M), the 200,000 TPM soft limit, the unpublished daily spend cap (429 REQUEST_LIMIT_EXCEEDED), released=false filtering, `neon credentials create --scope ai_gateway:invoke`, and the host format. One oddity: the models page also says 'Inference is free during the private preview', which conflicts with the prepaid-credit pricing on the overview. (<https://neon.com/docs/ai-gateway/models>)

Snippet checks:
- pgvector snippet: every line exists in the doc. However, `SET LOCAL hnsw.ef_search = 100;` only works inside a transaction block. The doc wraps it in BEGIN; ... SELECT ...; COMMIT;. Run standalone, Postgres raises a WARNING and the setting has no effect.
- Lakebase Search setup snippet: none. It matches the get-started page exactly.
- Hybrid RRF snippet: none. It matches the doc's TS example. It assumes the lakebase_bm25 index named 'documents_bm25' was created after inserting data.
- create-branch-action README example: `steps.create-branch.outputs.host` is not an output and resolves to empty; use `outputs.db_host`. `needs.setup.outputs.branch` needs a `setup` job plus `needs: setup`; without them it resolves to empty. `github.event.number` is also empty under workflow_dispatch, so branch_name becomes 'pr--'. The keys api_key, project_id, branch_name and expires_at are valid, and the 14-day expiry is under the 30-day max.
- delete-branch-action cleanup workflow: none. It matches the doc verbatim, and the inputs project_id, branch and api_key are valid in action.yaml.
- schema-diff-action snippet: the keys (project_id, compare_branch, api_key) and permissions match the README. However, it is a fragment: top-level `steps:` is not a valid workflow, so `permissions` and `steps` must sit under `jobs.<job_id>` (as in the README's second example), with `on:` and `runs-on:` added.
- Neon MCP Claude Code snippet: none. The command matches the connect-mcp-clients doc, and `?readonly=true` is the documented read-only parameter.
- AI Gateway OpenAI Python snippet: none. It matches the get-started page verbatim; base_url is {host}/v1 and model is gpt-5-mini (in the catalog).
