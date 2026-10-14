Hint Kata now has the config Vercel needs to run it. `pyproject.toml` names the app (`app.main:app`) for Vercel, `.python-version` pins 3.13, and `vercel.json` sets the function limit to 300 seconds and leaves tests, docs and caches out of the upload. Vercel cannot write next to the code, so the database must live in `/tmp` (set `HINTKATA_DB_PATH=/tmp/hintkata.db`). That means progress is not kept between instances until Postgres arrives. The content folder used to be found from the current directory; it is now found from the repo location, so the app boots from any folder, and a new test proves it. I did not create or link a Vercel project; the owner does that. Read `docs/runbooks/vercel.md` first: the checklist at the top lists what the owner must do.

Closes #56

🤖 Generated with [Claude Code](https://claude.com/claude-code)
