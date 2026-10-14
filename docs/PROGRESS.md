# Progress

Keep this current between tasks (the main session updates it; task PRs add a file under `docs/learning-log/` instead).

## Phase 1 — done (2026-10-14)
- M0 Bootstrap: public repo, ruleset, security scanning, Dependabot, CodeQL, 21 issues.
- M1 Harness (#22). M2 App skeleton (#23), Store (#24), Content loader (#27). M4.1 fetch_docs (#25).
- M3 Learning loop: quiz (#30), grader (#32), tutor (#31), checker (#26), review queue (#33), traces (#28), mastery map (#40), reveal re-test (#66).
- M4 Six lessons: PA1 (#36), PA2 (#37), FA1 (#35), FA2 (#34), GH1 (#38), GH2 (#39).
- M5 Acceptance suite (#62): fresh clone of main → `uv sync --locked`, ruff, ty, 248 tests + 94 acceptance tests green.
- Harness chore: hookify false positives tightened (#69).
- Still open for the owner: #19 grader calibration (needs OPENROUTER_API_KEY; steps are on the issue).

## Phase 2 — in flight
- Sources manifest for nine more lessons (#42 → PR #64, review done, merging)
- PostgresStore + pgvector schema + CI Postgres (#52 → PR #68, review fixes)
- Vercel config + runbook (#56 → PR #65, merging)
- Claude Code session-trace normaliser (#57 → PR #67, review fixes)
- Lessons being written: FA3 (#43), FA4 (#44), PA3 (#46), PA5 (#48), GH3 (#49), GH4 (#50)

## Next
- Lessons FA5 (#45), PA4 (#47), GH5 (#51); then the remaining ~7 lessons per track
- Full docs ingestion + embeddings via OpenRouter (#53), RAG tutor mode (#54), scheduled re-sync Action (#55)
- Owner actions needed before hosting: create a Neon project and type the two database URLs into the local env file and GitHub secrets (docs/runbooks/neon.md); link the Vercel project and set env vars (docs/runbooks/vercel.md); custom domain only after an explicit OK (#58)
- Phase 3 (#59–#61): accounts, payments, rate limits — outline only
