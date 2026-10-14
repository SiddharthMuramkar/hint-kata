# Progress

Keep this current between tasks (the main session updates it; task PRs add a file under `docs/learning-log/` instead).
Live numbers: run `uv run python scripts/docs_status.py --progress` and paste what is new.
Last checked: 2026-10-14, main at 15 lessons (5 per track).

## Phase 1 — done (2026-10-14)
- M0 Bootstrap: public repo, ruleset, security scanning, Dependabot, CodeQL, 21 issues.
- M1 Harness (#22). M2 App skeleton (#23), Store (#24), Content loader (#27). M4.1 fetch_docs (#25).
- M3 Learning loop: quiz (#30), grader (#32), tutor (#31), checker (#26), review queue (#33), traces (#28), mastery map (#40), reveal re-test (#66).
- M4 Six lessons: PA1 (#36), PA2 (#37), FA1 (#35), FA2 (#34), GH1 (#38), GH2 (#39).
- M5 Acceptance suite (#62): fresh clone of main → `uv sync --locked`, ruff, ty, 248 tests + 94 acceptance tests green.
- Harness chore: hookify false positives tightened (#69).
- Docs pass: PROGRESS, RESUME and the learning-log index brought up to date (#76).
- Still open for the owner: #19 grader calibration (needs OPENROUTER_API_KEY; steps are on the issue).

## Phase 2 — merged
- Lessons (nine, so 15 on main): FA3 (#71), FA4 (#74), FA5 (#100), PA3 (#72), PA4 (#102), PA5 (#75), GH3 (#73), GH4 (#70), GH5 (#101).
- Sources manifest: nine lessons (#64), the 21 remaining lessons (#103).
- Storage and hosting: PostgresStore + pgvector schema + CI Postgres (#68), Vercel config + runbook (#65).
- Docs for the tutor: ingestion with chunking, OpenRouter embeddings and pgvector upsert (#105), weekly re-sync Action (#99).
- Session traces: Claude Code session-trace normaliser with redaction (#67).
- Fixes: checker paths hardened (#106), `fastapi-cli` pinned so `uv run fastapi dev` works (#113).

## Phase 2 — in flight (open PRs)
- Lessons: FA6 (#107), PA6 (#108), GH6 (#110).
- RAG tutor mode with hybrid search and URL+anchor citations (#115, issue #54).
- Grader majority vote across three samples (#114, issue #112).
- Docs index script, regenerated learning log, this page (#116).

## Next (open Phase 2 issues with no PR yet)
- Lessons, 18 left: FA7–FA12 (#79–#84), PA7–PA12 (#86–#91), GH7–GH12 (#93–#98).
- Infra: make `openrouter_cache_instructions` effective in the tutor (#111).
- Owner steps: see the next section. #58 (custom domain) waits for an explicit OK.
- Phase 3 (#59–#61): accounts, payments, rate limits. Outline only.

## Owner-only steps
Claude never reads, prints or commits secrets. You type the values. Nothing is bought or linked without you.
1. `OPENROUTER_API_KEY`: run `gh secret set OPENROUTER_API_KEY -R siddharth-0044/hint-kata` (it asks for the value) and add the same key to your local env file. The grader calibration (#19), the docs embeddings and the RAG tutor need it. Set a spend cap on the key first.
2. Neon: create the project, then keep two database URLs, pooled and direct. Steps are in `docs/runbooks/neon.md`. The direct one also goes in as a secret: `gh secret set DATABASE_URL_UNPOOLED -R siddharth-0044/hint-kata`.
3. Vercel: link the project and set the env vars. Steps are in `docs/runbooks/vercel.md`.
4. GitHub setting for the re-sync plan job: Settings > Actions > General > Workflow permissions > tick "Allow GitHub Actions to create and approve pull requests". Steps are in `docs/runbooks/docs-resync.md`.
5. Custom domain (#58): only after you say yes in chat. Claude will not buy or point a domain before that.
