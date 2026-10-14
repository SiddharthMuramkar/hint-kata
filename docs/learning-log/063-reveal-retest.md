Peeking at an answer now counts as a miss: the item comes back for review soon instead of being forgotten. When a learner reveals a quiz item, the reveal handler makes an Again review card for it, capped to be due within 24 hours (the same "surprise" cap used for sure-but-wrong answers). When they reveal a deeper question, every rubric criterion gets its own Again card, because the learner never showed any of them. The reveal response now also carries `next_due`, the earliest due time as an ISO string. This follows SPEC section 7: a reveal is a signal that the idea is not yet learned. Read `app/routes/tutor.py` first (the `reveal` handler); the new tests are at the end of `tests/test_tutor.py`. No `tests/acceptance/` package exists yet, so no acceptance test was added.

Closes #63

🤖 Generated with [Claude Code](https://claude.com/claude-code)
