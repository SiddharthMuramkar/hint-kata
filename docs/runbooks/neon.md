# Neon setup

1. Create a free Neon project at neon.com. Pick the us-east region and Postgres 17 or newer (pgvector is built in; the search wants pgvector 0.8 or newer, which Neon ships on these versions).
2. Open the project's Connect dialog. Copy the pooled connection string (host contains `-pooler`).
3. Put it in the local env file as `DATABASE_URL=...`. The owner types this; never paste it into chat or git.
4. Turn off "Connection pooling" in the same dialog and copy the direct string. Put it in the local env file as `DATABASE_URL_UNPOOLED=...`.
5. Run `uv run python scripts/migrate.py`. It enables pgvector, creates the tables and prints `schema version 1`. It is safe to re-run.
6. For the later CI or deploy migrate step, store the direct URL as a repo secret: `gh secret set DATABASE_URL_UNPOOLED` (it prompts for the value).
7. Start the app as usual. With `DATABASE_URL` set it uses Postgres; unset it to go back to the SQLite file.
8. Why two URLs: the pooled one runs PgBouncer in transaction mode (no session `SET`, so use `SET LOCAL` inside a transaction); schema changes need the direct one.
9. To load the docs into search (chunks and embeddings), follow `docs/runbooks/ingestion.md`.
