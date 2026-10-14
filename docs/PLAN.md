# Hint Kata — build plan

Phase 1 in full. Phases 2 and 3 as outlines. Spec: `docs/SPEC.md`. Harness: `docs/HARNESS.md`.

## How the build runs
- **Models.** `F` = Fable 5.1 (main session: orchestration, splitting work, reviewing every diff, merging).
  `S` = Sonnet 5.5 at effort high (`builder` and `content-writer` subagents: all code, tests, config, content).
  `O` = Opus 5.5 (`second-opinion` subagent: read-only review of risky changes only; at most 3 calls in phase 1).
- **One task = one GitHub issue = one worktree = one branch = one PR.** Branch `issue-<n>-<slug>`.
  The PR body is a short plain-English lesson (what changed, why, which file to read first) and ends with `Closes #<n>`.
  The same text goes into a new file `docs/learning-log/<nnn>-<slug>.md` in the same PR; the main session updates `docs/PROGRESS.md` and the `docs/LEARNING_LOG.md` index between tasks (this avoids merge conflicts).
- **Per-task flow:** F picks the next issue → S works in its worktree → `uv run ruff check . && uv run ruff format --check . && uv run ty check && uv run pytest -q` pass locally → commit (trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`), push, `gh pr create` → `diff-reviewer` (F) reviews → S fixes → F runs `gh pr merge --auto --squash` → CI merges it.
- **Parallelism:** at most 2 worktree workers at once (24 GB Mac). Parallel pairs are marked below.
- **Cut-off safety:** push after every finished task; `docs/PROGRESS.md` says done / in flight / next; `docs/RESUME.md` holds the prompt to continue.
- **Definition of done (every task):** tests pass locally and in CI; ruff + ty clean; PR merged; issue closed; learning-log file added; nothing left only on the Mac.

## Phase 1 — local-first core

### M0 Bootstrap — model split: F 100% (O: 1 read-only review). ~0.5 session. No PRs possible yet.
| # | Task | Model | Tests / checks | Done when |
|---|---|---|---|---|
| 0.1 | `git init -b main`; `.gitignore`; first commit = `.gitignore`, `docs/`, minimal `.github/workflows/ci.yml` (job `checks`, placeholder test), `.github/dependabot.yml` | F | `git log` shows 1 commit | committed |
| 0.2 | `gh repo create hint-kata --public --source=. --remote=origin --push` (the ONLY direct push to main); `gh repo edit` squash-only, auto-merge, delete-branch-on-merge, allow-update-branch | F | `gh repo view` | repo exists, settings verified |
| 0.3 | Security: secret scanning + push protection, Dependabot alerts + security updates, CodeQL default setup (python, actions) — `gh api -H "X-GitHub-Api-Version: 2026-03-10"` | F | `gh api repos/… --jq .security_and_analysis` | all enabled |
| 0.4 | Wait for first CI run; read check name; create ruleset (require PR 0 approvals, required check `checks` id 15368, non-strict, block force-push/deletion, squash only, no bypass actors) | F, O reviews | `gh ruleset check main` | ruleset active |
| 0.5 | Labels, milestone "Phase 1", one issue per task in M1–M5 | F | `gh issue list --milestone "Phase 1"` | issues exist |
| 0.6 | `claude auto-mode defaults` → is "merge unapproved PR" soft or hard? Report; give the owner the one-line fix if needed | F | — | owner informed |

### M1 Harness — split: F 30% / S 60% / O 10%. ~1 session. One PR.
| # | Task | Model | Tests | Done when |
|---|---|---|---|---|
| 1.1 | `CLAUDE.md` (<200 lines, Resume-here section), `.claude/rules/*.md`, `.claude/agents/{builder,content-writer,diff-reviewer,second-opinion}.md`, `.claude/settings.json`, `.claude/hooks/ruff_after_edit.py`, hookify rules (committed), `.mcp.json`, `.env.example`, `.worktreeinclude`, `pyproject.toml` + `uv.lock`, full `ci.yml`, `evals` workflow (dispatch only) | S writes, F reviews, O reviews settings/permissions/CI | each hook + hookify rule tested by piping sample JSON; results pasted in the PR; CI green | merged |

### M2 App skeleton — split: F 20% / S 80%. ~1 session.
| # | Task | Model | Depends | Tests | Done when |
|---|---|---|---|---|---|
| 2.1 | FastAPI app, base template, dark theme (vendored CSS + licences), `/`, `/licenses`, footer, Markdown renderer with Pygments | S | 1.1 | page tests; XSS regression test | pages render |
| 2.2 | `Store` Protocol + `SqliteStore` + schema + migrations-by-version + tests | S, O reviews schema | 1.1 | store unit tests (temp DB) | merged |
| 2.3 | Content loader (lesson.md frontmatter, quiz/deeper/warmup YAML, sources.yaml), lesson page with sections + attribution footer, `sources.yaml` validation test | S | 2.1 | loader tests with a fixture lesson | fixture lesson renders |
Parallel pair: 2.1 ∥ 2.2; then 2.3 ∥ 4.1.

### M3 Learning loop — split: F 20% / S 80%. ~2–3 sessions.
| # | Task | Model | Depends | Tests | Done when |
|---|---|---|---|---|---|
| 3.1 | Quiz engine: item types, per-option feedback, confidence tags, second try, surprise callout, scoring | S | 2.2, 2.3 | engine unit tests; page test | all item types work on the fixture lesson |
| 3.4 | Grader agent (NativeOutput schema, 3-sample majority, untrusted wrapper, injection flag) + think-deeper UI (revisions, model answer) + `evals/grader/` skeleton | S | 2.2, 2.3 | FunctionModel tests for every branch | works offline in tests |
| 3.5 | Tutor agent + SSE endpoint + JS chat + hint ladder enforced in code + citation validation + history + reveal | S | 2.3 | ceiling tests (deterministic); SSE format test; one live-stream test with uvicorn thread | streams on the fixture lesson |
| 3.6 | Hands-on checker: workspace copy, pytest runner with timeout, `gh` check runner for GitHub tasks, results page | S | 2.3 | runner tests with a tiny fixture task | passes/fails correctly |
| 3.2 | fsrs review queue: cards from misses and unmet criteria, rating map, `/today`, review API | S | 3.1, 3.4 | scheduler tests with fixed clock | due cards appear and reschedule |
| 3.7 | Trace player + `traces/scripts/` (FunctionModel run; PR timeline via gh) + predict checkpoints + CI snapshot test | S | 2.3 | generator snapshot tests | both trace kinds play |
| 3.3 | Mastery rule + map on `/`, thresholds in config, events log | S | 3.1, 3.2, 3.6 | rule unit tests | map updates |
Parallel pairs: 3.1 ∥ 3.4 → 3.5 ∥ 3.6 → 3.2 ∥ 3.7 → 3.3.

### M4 Content — split: F 35% (accuracy review against the cache) / S 65%. ~2 sessions.
| # | Task | Model | Depends | Tests | Done when |
|---|---|---|---|---|---|
| 4.1 | `scripts/fetch_docs.py` (FastAPI raw at tag, Pydantic AI index.md with preamble stripped, GitHub Article API; sha256 + fetched_at; `--check` offline) + `sources.yaml` entries for all 6 lessons | S | 2.3 | unit tests with recorded fixtures; `--check` in CI | cache fills on the Mac |
| 4.2 | Lesson PA1 — Your first agent (`Agent`, instructions, model strings, `output_type`) + quiz + deeper + task (pytest, TestModel) | content-writer S | 3.x | content validation + checker passes on solution, fails on starter | merged |
| 4.3 | Lesson FA1 — Dependencies (`Depends`, `Annotated`, yield, scope) + task (TestClient) | S | 3.x | same | merged |
| 4.4 | Lesson PA2 — Tools and dependencies (`@agent.tool`, `RunContext`, deps) + task (FunctionModel) + trace (tool call + ModelRetry) | S | 3.x, 3.7 | same + trace snapshot | merged |
| 4.5 | Lesson FA2 — Testing (`TestClient`, `dependency_overrides`) + task (learner's tests must pass on good app, fail on buggy app) | S | 3.x | same | merged |
| 4.6 | Lesson GH1 — Is this PR ready to merge? (branches, PRs, reviews, checks, rulesets) + `check.yaml` (gh checks on the practice repo) + trace (this repo's own PR timeline) | S | 3.x, 3.7 | content validation; check runner dry-run | merged |
| 4.7 | Lesson GH2 — Your first CI workflow (Actions quickstart, workflow syntax, python tutorial) + `check.yaml` | S | 3.x | same | merged |
Parallel pairs: 4.2 ∥ 4.3 → 4.4 ∥ 4.5 → 4.6 ∥ 4.7. Every lesson PR is reviewed by F against the cached source text for accuracy and attribution.

### M5 Acceptance — split: F 40% / S 60%. ~1 session.
| # | Task | Model | Depends | Done when |
|---|---|---|---|---|
| 5.1 | `tests/acceptance/` covering every row of SPEC §23 | S | M3, M4 | green in CI |
| 5.2 | Grader calibration: owner labels 20–30 answers for 2 rubrics; run `evals/grader`; report kappa; adjust rubric text | F (+ owner's key) | 3.4, 4.x | kappa reported in LEARNING_LOG |
| 5.3 | Docs pass: PROGRESS, RESUME, LEARNING_LOG, HARNESS "what changed" | F | all | `/goal` condition met |

### Model split per milestone (one line each)
M0 F · M1 F 30 / S 60 / O 10 · M2 F 20 / S 80 (O: schema review) · M3 F 20 / S 80 · M4 F 35 / S 65 · M5 F 40 / S 60.
Fable carries judgment and review; Sonnet carries code and content; Opus appears 3 times.

### Session estimate
About 8 working sessions, assuming weekly usage cut-offs. Each session starts from `docs/RESUME.md`.

### /goal and /loop lines (owner types them; see HARNESS.md for caveats)
- `/goal Phase 1 is done: every issue in milestone "Phase 1" is closed, and on a fresh checkout of origin/main "uv run pytest -q" and "uv run pytest tests/acceptance -q" exit 0 with no skips; print each command's final output as proof; or stop after 80 turns`
- `/loop 15m run gh pr list --state open and gh pr checks for each; for any failed required check read gh run view --log-failed, send the fix to that PR's builder, and report; if all green say so`

## Phase 2 — hosted + full content (outline)
1. `PostgresStore` on Neon (Free → Launch), Alembic migrations on the unpooled URL, psycopg 3 pooled URL at runtime.
2. Full docs ingestion: include resolvers, heading chunks, embeddings via OpenRouter, pgvector HNSW + tsvector GIN, hybrid RRF search, citations by URL + anchor; tutor switches to RAG.
3. Weekly re-sync GitHub Action (off-hour cron + dispatch) that opens a PR with the content diff; embed on merge.
4. Remaining lessons to ~10–12 per track, generated by `author` from the cache and reviewed in PRs.
5. Claude Code session traces (SessionEnd hook → inbox → normaliser → human review).
6. Vercel: FastAPI zero-config, Hobby while non-commercial, Deployment Protection, preview env; one static Neon `preview` branch; later the Neon-managed integration.
7. Domain `hintkata.com` (ask before buying); Logfire free plan; hosted hands-on checks.

## Phase 3 — accounts and payments (outline)
GitHub OAuth (or Neon Managed Better Auth), per-user data, payments provider (research then), Vercel Pro,
rate limits on LLM endpoints, privacy policy, licence/trademark review, remove or license Claude Code doc content.
