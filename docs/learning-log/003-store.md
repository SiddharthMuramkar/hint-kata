This PR adds the part of the app that remembers things: a small SQLite database behind a `Store` interface. `app/schema.sql` creates the tables from the spec (users, attempts, grades, review cards, chats, checks, mastery, events). `app/store.py` has a `Store` Protocol, which is just a list of method names, and `SqliteStore`, which does the real work. Every SQL string lives inside `SqliteStore`, so a Postgres version can replace it in phase 2 without touching the rest of the app. Two SQLite traps are handled in `connect()`: the foreign-key and WAL settings are applied before transactions are switched on (otherwise SQLite silently ignores them), and the connection may be used from another thread, because FastAPI can do that within one request. Dates are saved as UTC text, which sorts correctly. Read `app/store.py` first, then `tests/test_store.py` to see each method used.

Closes #3

🤖 Generated with [Claude Code](https://claude.com/claude-code)
