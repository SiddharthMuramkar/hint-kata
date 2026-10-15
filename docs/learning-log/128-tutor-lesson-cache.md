## What changed

The tutor now caches the lesson text as well as its rules. Before, one cache marker covered only the fixed rules (about 2,900 characters). The lesson sections, the biggest part of the prompt (up to 12,000 characters), were sent fresh on every turn.

How it works now:

- `make_tutor(model, lesson)` builds one tutor agent per lesson. Its static instructions are the rules (`STATIC_INSTRUCTIONS`) followed by that lesson's sections text, so the one `openrouter_cache_instructions` marker covers both. The cache is a prefix, so one marker at the end of the block is enough.
- The route's `get_tutor(lesson)` keeps these agents in an `lru_cache` of 64, keyed on the sections text itself. Two lessons give two agents, and an edited lesson gives a new one, so a stale cached block is never reused.
- The per-turn part (`_instructions`) is still dynamic and has no marker: lesson title, attempts, ceiling, misconceptions, stuck line. Retrieved docs stay in the learner's turn.
- `TutorDeps` lost its `sections` field. The text is now the agent's cache key instead.

Why not a second marker: Pydantic AI 2.56.0 marks only static instruction parts, so one block holding both is the way to reach the lesson text without a `CachePoint` in the user prompt (which the research notes warn against).

Tests: the MockTransport wire test in `tests/test_tutor_cache.py` now shows the first system block holds the rules and the sections, carries `cache_control` once, the per-turn part and user turn carry none, and a different or edited lesson gives a different block. Because the agent is built per lesson, the old `get_tutor().override(model=...)` in tests could no longer reach the agent the route uses. A small helper `fake_tutor(model)` in `tests/test_tutor.py` now puts the fake model on every lesson's agent. Lesson PA6 describes the new layout.

Read first: `make_tutor` in `app/agents/tutor.py`.

Closes #128
