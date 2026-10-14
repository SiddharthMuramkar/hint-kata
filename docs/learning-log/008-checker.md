Each hands-on lesson can now check the learner's work. For Pydantic AI and FastAPI lessons, `starter/` is copied once into `workspace/<lesson-id>/` and the hidden tests run there in a subprocess with a 120 s timeout, using the app's own Python so no extra install is needed. Secrets (anything with KEY, TOKEN or SECRET in its name) are stripped from the environment of that subprocess. For GitHub lessons, `check.yaml` lists read-only `gh` calls and the expected output of each, matched exactly or with a `re:` regex. The result is saved in the `checks` table, and `POST`/`GET /api/check/{lesson_id}` expose it. A small partial and about 20 lines of JS add the "Check my work" button. Start by reading `app/checker.py`; the tests in `tests/test_checker.py` show every case, including the timeout and a fake `gh` on PATH.

Closes #8

🤖 Generated with [Claude Code](https://claude.com/claude-code)
