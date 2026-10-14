# Progress

Keep this current between tasks (the main session updates it; task PRs add a file under `docs/learning-log/` instead).

## Done
- 2026-10-14 — Scoping: research (3 waves, fact-checked) in `docs/research/`; SPEC, PLAN, HARNESS, RESUME, PARKING_LOT, LEARNING_LOG written.
- 2026-10-14 — M0 Bootstrap: public repo `hint-kata`, squash-only + auto-merge, ruleset `protect-main` (PR required, check `checks` required, no force-push/deletion), secret scanning + push protection, Dependabot alerts/updates, CodeQL default setup, milestone "Phase 1" with 21 issues (#1–#21).
- 2026-10-14 — M1 Harness (#1 → PR #22): CLAUDE.md, agents, rules, settings, ruff hook, 8 hookify rules, .mcp.json, .env.example.
- 2026-10-14 — M2.1 App skeleton (#2 → PR #23): FastAPI + Jinja2, dark theme, safe Markdown, all phase-1 pins.
- 2026-10-14 — M2.2 Store (#3 → PR #24): SQLite store behind a `Store` protocol.
- 2026-10-14 — M4.1 fetch_docs (#11 → PR #25): fetch script, `content/sources.yaml` with hashes for all 26 pages.

## In flight
- #4 content loader (PR #27, in review) · #8 hands-on checker (PR #26, review fixes) · #10 trace player (PR #28, in review)
- #5 quiz engine, #6 grader, #7 tutor — builders running (branched from #27/#26)

## Next
- #9 review queue (after #5), #21 mastery map (after #5, #9, #8)
- Lessons #12–#17 (after #4 and the learning-loop tasks), then #18 acceptance, #19 calibration, #20 docs pass
