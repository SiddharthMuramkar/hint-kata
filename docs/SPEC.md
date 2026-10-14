# Hint Kata — product spec

Status: approved scope, 2026-10-14. Phase 1 is specified in full. Phases 2 and 3 are outlines.
Research behind every claim: `docs/research/` (start with `INDEX.md`).

## 1. Problem

Reading docs does not make things stick. The owner has built FastAPI apps before and still feels shaky.
Hint Kata turns three doc sets into short lessons with retrieval practice, graded open questions, hands-on
tasks, and a tutor that hints before it answers. It is built with the stack it teaches, so the repo itself is
a worked example.

## 2. Users

- **Phase 1:** the owner only. The site runs on their Mac. One local user record.
- **Phase 2:** still the owner, but hosted (Vercel + Neon) so it works from any device.
- **Phase 3:** newcomers with accounts; paid access.

Every table carries a `user_id` from day one so accounts can be added without a data migration.

## 3. Phases and scope

### Phase 1 — local-first core (in full)
- Runs with `uv run fastapi dev` on the Mac. No cloud services except OpenRouter (LLM API) and GitHub.
- 3 tracks × 2 lessons (6 lessons). Each lesson: warm-up, reading, optional trace, quiz, think-deeper, hands-on, tutor.
- Spaced review queue ("Today" page), confidence tags, mastery map, watch-it-run traces.
- Content fetched from official sources into a gitignored cache; lessons written in our own words with links and attribution.
- Data in SQLite behind a small store interface.
- GitHub from day one: public repo, issues, PRs, CI, auto-merge, rulesets, secret scanning, Dependabot, CodeQL.

### Phase 2 — hosted + full content (outline, §18)
### Phase 3 — accounts and payments (outline, §19)

## 4. Non-goals (phase 1)
- No accounts, login, payments, or multi-user data.
- No vector database or embeddings. The tutor uses the current lesson's text.
- No JS framework, no JS build step, no in-browser Python.
- No hosting, no domain.
- No Claude Code session transcripts as content (phase 2). No GitHub-track content about Claude Code itself in phase 1 (its docs have no reuse licence; lessons will link, not ingest).
- No automated AI review bot on GitHub (claude-code-action) — rejected, see `docs/HARNESS.md`.

## 5. User flows (phase 1)

1. **Open the site** → home shows 3 tracks, each lesson's mastery state, and a "Today" link with the number of due reviews.
2. **Start a lesson** → warm-up questions (ungraded) → reading (short sections with doc links and attribution) →
   trace player (if the lesson has one) → quiz → think-deeper → hands-on → "Done" (mastery updates).
3. **Ask the tutor** → a chat panel on the lesson page. Replies stream. Each reply ends with citations to lesson
   sections and source links. Hints come before answers (§7).
4. **Review** → `/today` lists due cards. Answer each; rate is derived from correctness + confidence; fsrs schedules the next time.
5. **Check hands-on work** → "Check my work" runs the lesson's checker and shows pass/fail and output.

## 6. Lesson, quiz and grading design

Rules come from `docs/research/learning-science.md`.

### 6.1 Lesson file set (`content/<track>/<lesson-id>/`)
- `lesson.md` — frontmatter (id, track, title, version pins, sources with licence and attribution text, estimated minutes), then sections with stable ids (`## Dependencies {#deps}`), each 3–5 minutes of reading. Our own words. Every factual section links to its source.
- `warmup.yaml` — 1–2 ungraded predict questions shown before the reading.
- `quiz.yaml` — 4–6 items. Types: `single` (one correct; each option has `misconception` + `feedback`), `order` (steps to arrange), `blank` (fill in the code blank; exact or regex match). Each item has `concept` (for cards) and `source_section`.
- `deeper.yaml` — 2 open questions. Each has `rubric`: 3–5 binary criteria with `explanation`, `pass_anchor`, `fail_anchor`; plus `model_answer` and `hints` (2).
- `task/` — `README.md` (what to do), `starter/` (files copied to the learner's workspace), `tests/` (hidden checks) or `check.yaml` (for the GitHub track: list of `gh` checks).
- `trace.json` (optional) — see §8.
- `content/sources.yaml` — every source URL, pinned version or fetch date, sha256, licence, attribution text.

### 6.2 Quiz behaviour
- One item at a time. Learner picks an answer and a confidence tag: Sure / Think so / Guessing.
- Feedback right after each item: why the chosen option is tempting and wrong, or why it is right.
- A second try is allowed after reading the feedback; it counts as "Hard" for scheduling.
- A confident wrong answer gets a "surprise" callout and comes back as a review card due tomorrow.
- Score per lesson = first-try correct / items.

### 6.3 Think-deeper grading
- Each grader sample returns, per criterion: `evidence` (quote from the answer), `reasoning`, `met` (bool); plus one line of feedback and one hint per unmet criterion.
- The learner may revise up to 2 times. After the last try the model answer is shown.
- The grader runs 3 samples. Per criterion, `met` is true when at least 2 of the 3 samples say met (a sample with no verdict counts as not met), and `uncertain` is true when the 3 samples do not all agree (a 2-1 or 1-2 split). `uncertain` is only a label ("the grader's three readings disagreed; your answer may be borderline"): it never blocks progress, so a 2-of-3 pass counts as met. The criterion's `evidence` comes from the first sample that agrees with the majority, and its `hint` (unmet criteria only) from that same sample.
- Length and formatting earn nothing (stated in the rubric prompt).
- The learner's answer is wrapped in delimiters and declared untrusted. Manipulation phrases ("ignore the rubric", "full marks") set a flag and score 0.
- Calibration: `evals/grader/*.yaml` holds owner-labelled answers (including verbose-wrong, terse-right, synonym, injection). Target agreement kappa ≥ 0.7 per criterion before a rubric is trusted.

## 7. Tutor design

- Context per turn: lesson text (with section ids), the learner's recent attempts and misconceptions, the chat history for this lesson, and the current hint ceiling.
- Hint ladder, enforced in code (the server sets the ceiling, the prompt only describes the rungs):
  L0 restate the goal / ask what was tried → L1 point to the lesson section or doc link → L2 leading question →
  L3 the approach in words → L4 a worked example on a different problem → L5 code with blanks → L6 full answer.
- Ceiling rules: during an active quiz item, max L2. Ceiling rises by one rung per learner attempt. Asking for the answer never raises it by itself. A "Show me" button reveals L6 after a one-line cost message; it logs the reveal and schedules a re-test.
- After 2 turns with no progress the tutor names the error and gives the next rung (no Socratic loops).
- Citations: the reply contains `[§section-id]` markers. The server keeps only markers that match this lesson's sections and renders them as links (section anchor + the section's source URL). Invalid markers are dropped.
- Streaming over SSE; final reply stored in `chats` so a refresh keeps the history.

## 8. Watch-it-run traces

A trace transcript is a curated, step-indexed replay of a real run. Phase 1 has two kinds:
- `pydantic_ai_run`: generated by `traces/scripts/<name>.py` with `FunctionModel` (scripted, realistic tool calls, no API cost). Steps: user_prompt, instructions, model_request, tool_call, tool_result, retry, final_output, with token counts.
- `github_pr`: built by `traces/scripts/pr_timeline.py` from this repo's own PR via `gh api` (commits, PR opened, CI check, review, merge).
Each step has `summary`, `payload_excerpt`, `annotation` (why + concept tags + doc links) and an optional checkpoint (`predict_next` single-choice). The player shows one step at a time with a progress bar and pauses at checkpoints. Trace payloads are data, never instructions; the tutor may refer to steps but cites only docs.

## 9. Review queue and mastery

- Cards: one per quiz `concept` and one per unmet rubric criterion (`met` false; a criterion that is met but `uncertain` makes no card). Stored as fsrs `Card` JSON + `due` (ISO UTC).
- Rating map: wrong → Again; correct after a hint or second try, or "Guessing" → Hard; correct + "Sure"/"Think so" → Good; correct + Sure + fast (< 10 s) → Easy.
- `desired_retention` 0.9 (config). Review items are sibling questions where available, else the same item.
- Mastery per lesson: `learning` after first visit; `mastered` when quiz ≥ 80% first-try AND every concept recalled correctly without hints on two different days AND the hands-on check passed. Threshold values live in config and every change is logged.
- Mastery map on the home page: per track, per lesson: not started / learning / mastered.

## 10. Hands-on checks

- Pydantic AI and FastAPI lessons: `starter/` is copied to `workspace/<lesson-id>/` (gitignored). "Check my work" runs `uv run pytest -q <hidden tests> --rootdir workspace/<lesson-id>` in a subprocess with a 120 s timeout and shows output. Tests use `TestModel`/`FunctionModel` so no API key is needed. Pass/fail is stored in `checks`.
- GitHub lessons: the learner works in their own public practice repo (`PRACTICE_REPO=owner/name` in `.env`). The checker runs read-only `gh api` calls listed in `check.yaml` (e.g. a ruleset on main requires a PR; a PR exists from a non-main branch; a workflow run exists for that PR; its check is required) and shows each result.
- Checks are self-reported in phase 1 (single user). Server-side verification waits for phase 3.

## 11. Content pipeline

### Phase 1
- `scripts/fetch_docs.py` reads `content/sources.yaml` and downloads only the listed pages into `.cache/docs/<source>/...` (gitignored): FastAPI from `raw.githubusercontent.com/fastapi/fastapi/<tag>/docs/en/docs/<path>.md` (tag 0.143.0); Pydantic AI from `https://pydantic.dev/docs/ai/<slug>/index.md` (strip the injected preamble) or raw GitHub at tag v2.56.0; GitHub Docs from `https://docs.github.com/api/article/body?pathname=/en/...`. It records sha256 + fetched_at back into `sources.yaml` (`--update`).
- Lessons are written from the cache in our own words. Attribution footer per lesson: source title, URL, version/date, licence (MIT for FastAPI/Pydantic AI with copyright line; CC BY 4.0 for GitHub Docs with "adapted" note). A `/licenses` page shows the full MIT texts and the CC BY link. The site says it is not affiliated with GitHub, FastAPI or Pydantic.
- Claude Code docs: link only; short original summaries. MCP docs (CC BY 4.0) may be quoted with attribution.
- A CI test checks every lesson's sources exist in `sources.yaml` with a licence and attribution text.

### Phase 2 (outline)
Full ingestion with heading-aware chunking, include resolvers, embeddings via OpenRouter (`openai/text-embedding-3-small`, 1536 dims) into Neon pgvector + tsvector hybrid search (RRF), weekly re-sync Action that opens a PR with the content diff; citations = page URL + anchor. Details: `docs/research/rag-and-content-pipeline.md`.

## 12. Tracing and testing the LLM parts

- Unit tests never call a model: `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False` in `conftest.py`; agents are exercised with `TestModel` / `FunctionModel` via `agent.override(...)`.
- Contract tests for prompts: the hint ceiling is enforced in code, so tests assert that the server truncates or rejects L6 content when the ceiling is L2 (deterministic filter).
- Evals (`evals/`): pydantic-evals datasets for the grader (owner-labelled answers) and the tutor (hint-before-answer rubric, citation validity). Run by hand (`uv run python -m evals`) or by the `evals` GitHub Actions workflow on `workflow_dispatch` only. Judge model is set explicitly to `JUDGE_MODEL` (the default would be `openai:gpt-5.2`).
- Tracing: `logfire.configure(send_to_logfire="if-token-present")` + `instrument_pydantic_ai()` + `instrument_fastapi(app)`. Works without an account; with a free Logfire token the owner can inspect runs. `include_content` on in phase 1 (single user), off by default from phase 3.
- Cost guard: `UsageLimits` per run; `max_tokens` set on every agent; OpenRouter key capped in the dashboard; cost per request read from `provider_details`.

## 13. Architecture (phase 1)

- Python 3.13 (uv-managed). FastAPI 0.143.x + Jinja2 templates + StaticFiles. Built-in SSE (`fastapi.sse`) for the tutor; browser side is ~35 lines of vanilla JS (`fetch` + stream reader).
- Markdown → HTML on the server with `markdown-it-py` (`js-default` preset, html off) + `gfm_plugin` + `anchors_plugin`; Pygments (`nowrap`) with the `github-dark` style; CSS: vendored `github-markdown-css` (dark-dimmed) + `app.css` with six Primer colour tokens.
- Pydantic AI 2.56 via OpenRouter. Agents in `app/agents/`: `tutor`, `grader`, `author` (scripts only). Model slugs from env.
- SQLite in `data/hintkata.db` (WAL, foreign keys on, one connection per request). `app/store.py` defines a `Store` Protocol and `SqliteStore`; a `PostgresStore` drops in at phase 2.
- Layout: `app/` (main.py, routes/, agents/, store.py, markdown.py, templates/, static/), `content/`, `traces/`, `scripts/`, `evals/`, `tests/` (unit, acceptance), `docs/`.

## 14. Data model (SQLite, phase 1)

```
users(id PK, name, created_at)
attempts(id PK, user_id FK, lesson_id, item_id, kind quiz|warmup|review, answer, correct bool, confidence sure|thinkso|guessing, try_no, elapsed_ms, created_at)
grades(id PK, user_id FK, lesson_id, question_id, attempt_no, answer, result_json, flagged bool, created_at)
cards(id PK, user_id FK, item_key UNIQUE(user_id,item_key), lesson_id, card_json, due TEXT, last_rating, updated_at)
review_logs(id PK, card_id FK, log_json, created_at)
chats(id PK, user_id FK, lesson_id, role user|assistant, content, ceiling, citations_json, created_at)
checks(id PK, user_id FK, lesson_id, passed bool, output, created_at)
mastery(user_id FK, lesson_id, state notstarted|learning|mastered, updated_at, PRIMARY KEY(user_id, lesson_id))
events(id PK, user_id FK, kind, data_json, created_at)   -- reveals, surprises, threshold changes
```
Datetimes are ISO-8601 UTC text. Lesson/item ids are strings from the content files.

## 15. Pages and API

Pages (HTML): `GET /` home + mastery map · `GET /today` · `GET /lessons/{id}` · `GET /licenses`.
API (JSON unless noted):
- `POST /api/quiz/{lesson}/{item}` {answer, confidence, try_no} → {correct, feedback, misconception, card_due}
- `POST /api/deeper/{lesson}/{q}` {answer} → {criteria:[{name, met, uncertain, evidence, hint}], feedback, hints, flagged, all_met, attempt_no, can_retry, model_answer?}
- `POST /api/tutor/{lesson}` {message} → SSE events `token`, `html`, `citations`, `error`
- `POST /api/tutor/{lesson}/reveal` → logs the reveal, returns the model answer for the current item
- `POST /api/check/{lesson}` → {passed, output, details}
- `POST /api/review/{card}` {answer, confidence, elapsed_ms} → {correct, next_due}
- `GET /api/trace/{lesson}` → trace JSON · `POST /api/trace/{lesson}/{step}` {choice} → {correct, explanation}
- `GET /api/progress` → mastery + due counts (used by the home page)

## 16. Configuration

`.env` (gitignored; `.env.example` lists names only):
`OPENROUTER_API_KEY`, `TUTOR_MODEL` (default `openrouter:anthropic/claude-haiku-5.5`), `GRADER_MODEL`
(`openrouter:anthropic/claude-sonnet-5.5`), `AUTHOR_MODEL` (same), `JUDGE_MODEL` (same as grader),
`OPENROUTER_ZDR` (true/false), `OPENROUTER_APP_TITLE` (`hint-kata`), `HINTKATA_DB_PATH` (`data/hintkata.db`),
`PRACTICE_REPO` (`owner/name`), `LOGFIRE_TOKEN` (optional), `DESIRED_RETENTION` (0.9).

## 17. Security and privacy

- Public repo: no secrets, no personal paths, no learner data in git (`.env`, `data/`, `workspace/`, `.cache/` are gitignored). Secret scanning + push protection on.
- LLM output and learner input are untrusted: Markdown rendered with raw HTML disabled; a regression test checks `<script>` and `javascript:` never survive; citations are validated server-side.
- Hands-on checkers run learner code locally on purpose (it is the learner's own machine). Timeouts apply.
- OpenRouter: training opt-out in account settings; optional ZDR routing; per-key spend cap.

## 18. Phase 2 outline — hosted + full content
Neon Lakebase Postgres (Free → Launch), `PostgresStore`, pgvector + tsvector hybrid retrieval, full docs ingestion and weekly re-sync PRs, embeddings via OpenRouter, remaining lessons (to ~10–12 per track), Claude Code session traces, Vercel (FastAPI zero-config; Hobby while non-commercial; Deployment Protection), custom domain `hintkata.com` (ask before buying), Logfire free plan, hosted hands-on checks. Research: `docs/research/{neon,vercel,rag-and-content-pipeline,trace-transcripts}.md`.

## 19. Phase 3 outline — accounts and payments
GitHub OAuth (or Neon Managed Better Auth once separate backends are supported), per-user data (already keyed), payments provider (research then), Vercel Pro (Hobby forbids commercial use), rate limits and abuse protection on the LLM endpoints, privacy policy, licence and trademark review before selling (Claude Code docs excluded from any sold content unless licensed).

## 20. Plan tiers and rough monthly cost
| Item | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| GitHub | Pro (already paid, ~$4) — everything needed is free on a public repo | same | same |
| OpenRouter | one-time credit (e.g. $10 + 5.5% fee); usage ≈ $1–5/month for one learner (Haiku tutor, Sonnet grader) | +embeddings ≈ $0.05 per full re-embed | scales with users; cap per key |
| Vercel | — | Hobby $0 | Pro $20 |
| Neon | — | Free $0 → Launch $3–10 | Launch/Scale |
| Domain | — | ~$11–13/yr | same |
| Logfire | optional, free | free | free/Team $49 |
Total: phase 1 ≈ $5–10/month; phase 2 ≈ $5–35; phase 3 ≈ $40–75. Ceiling agreed: $75/month.

## 21. Risks (phase 1)
- Content staleness: Pydantic AI ships ~4 releases a week; FastAPI breaks in minor versions. Mitigation: exact pins, version stamps on lessons, CI runs the lesson code, re-sync later.
- Grader reliability: Claude 5.5 rejects temperature; variance between runs. Mitigation: binary criteria with anchors, 3-sample majority, calibration set, "uncertain" label.
- Tutor leaks answers or stalls in Socratic loops. Mitigation: ceiling enforced in code; no-progress escalation; eval set of "just give me the answer" prompts.
- Auto mode may block `gh pr merge` ("PR no human approved"). Mitigation: checked at bootstrap; explicit user intent / user-scope allow.
- GitHub may hold "unproven" workflow runs on public repos for browser approval. Mitigation: owner approves; nothing else to do.
- Usage cut-offs mid-task. Mitigation: small PRs, push after each task, PROGRESS.md + RESUME.md.
- RAM: two worktrees with their own `.venv` and dev servers. Mitigation: cap 2 parallel workers; `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS=3`.

## 22. Open questions (not blocking phase 1)
- Does `Embedder('openrouter:...')` work end to end? (phase 2; verified from source only)
- Is the auto-mode "merge unapproved PR" rule soft or hard? (checked at bootstrap, step 0.6)
- Should think-deeper grading use Haiku after calibration to cut cost? (decide after the calibration run)
- Which practice-repo flow is least confusing for the GitHub track: one repo reused across lessons, or one per lesson?

## 23. Acceptance criteria — phase 1 (each maps to tests in `tests/acceptance/`)

| Feature | Acceptance criteria |
|---|---|
| App runs | `uv sync --locked && uv run fastapi dev` serves `/` on a fresh clone with only `.env` present; no 5xx in the log; dark theme applied; "not affiliated" footer present. |
| Content loads | All 6 lessons render; every section has an anchor; every lesson's sources are in `sources.yaml` with licence + attribution; `scripts/fetch_docs.py --check` passes offline against recorded hashes. |
| Warm-up | Shown before the reading; answers stored as `kind=warmup`; not counted in scores. |
| Quiz | Per-option feedback shown after each answer; confidence stored; second try counts as Hard; confident-wrong creates a card due within 24 h; score = first-try correct / items. |
| Think-deeper | Grader returns per-criterion met (majority of 3 samples) and uncertain (samples not unanimous) with evidence; revisions capped at 2; model answer after the last try; injection phrases flagged and scored 0; works with `FunctionModel` in tests. |
| Tutor | Streams tokens over SSE; final HTML replaces the text; citations only to valid section ids; ceiling ≤ L2 during an active quiz item verified by a deterministic test; history survives a page refresh; "Show me" logs a reveal event and schedules a re-test. |
| Hands-on | "Check my work" passes on the reference solution and fails on the starter for all 4 Python tasks; GitHub tasks run their `gh` checks and show each result; output shown to the learner; timeout enforced. |
| Traces | Both trace kinds play step by step; predict checkpoints graded; trace generator scripts re-run in CI and produce identical step structure. |
| Review queue | `/today` lists due cards; answering updates fsrs state and `due`; rating map as in §9; no card for an unseen concept. |
| Mastery | Mastery rule as in §9 with thresholds in config; map on `/` reflects state after each action. |
| Safety | `<script>`/`javascript:` never survive rendering; `.env`/`data/`/`workspace/` never tracked by git (test checks `.gitignore`). |
| CI | `checks` job (ruff, ruff format, ty, pytest) green on main; no network or model calls in tests. |
| Docs | `docs/PROGRESS.md`, `docs/LEARNING_LOG.md` updated in every PR; `docs/RESUME.md` prompt works from a fresh clone. |
