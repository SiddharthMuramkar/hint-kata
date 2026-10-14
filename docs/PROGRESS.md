# Progress

Keep this current between tasks (the main session updates it; task PRs add a file under `docs/learning-log/` instead).

## Done
- 2026-10-14 — Scoping: research (3 waves, fact-checked) in `docs/research/`; SPEC, PLAN, HARNESS, RESUME, PARKING_LOT, LEARNING_LOG written.
- 2026-10-14 — M0 Bootstrap: public repo `hint-kata`, squash-only + auto-merge, ruleset `protect-main`, secret scanning + push protection, Dependabot, CodeQL default setup, milestone "Phase 1" with 21 issues.
- 2026-10-14 — M1 Harness (#1 → PR #22). M2 App skeleton (#2 → #23), Store (#3 → #24), Content loader (#4 → #27). M4.1 fetch_docs (#11 → #25).
- 2026-10-14 — M3 Learning loop: quiz engine (#5 → #30), grader (#6 → #32), tutor (#7 → #31), hands-on checker (#8 → #26), review queue + Today (#9 → #33), trace player + generators (#10 → #28).

## In flight
- #21 mastery map (PR #40, in review)
- Lessons: PA1 (#12 → PR #36), FA1 (#13 → #35), PA2 (#14 → #37), FA2 (#15 → #34), GH1 (#16 → #38), GH2 (#17 → #39) — all in review

## Next
- #18 acceptance tests (after the lessons merge), #19 grader calibration (needs the owner's OPENROUTER_API_KEY), #20 docs pass
- Housekeeping found in review: exclude content tasks from `ty`, `white-space: pre-wrap` for quiz prompts, `content.validate()` for `re:` blank answers (see docs/PARKING_LOT.md)
- Known hookify false positive: one Bash command containing `git push` and, later, the word `main` (e.g. `--base main`) is blocked — run the push as its own command
