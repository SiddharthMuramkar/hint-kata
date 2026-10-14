# Runbook: put the docs into search (ingestion)

This turns the cached docs pages into small chunks, gives each chunk an embedding (a list of numbers that
captures its meaning), and stores them in Neon next to a keyword index. Search then combines both.
You run it from your own laptop. Nothing here runs on Vercel.

## Before you start
- Neon is set up and `scripts/migrate.py` has run once (`docs/runbooks/neon.md`).
- The docs pages are in `.cache/docs/` (run `uv run python scripts/fetch_docs.py` if that folder is empty).

## 1. Put the keys in the local env file
Open the local env file in VS Code (Explorer, next to `.env.example`) and fill in two names:
- `OPENROUTER_API_KEY` is your OpenRouter key. Give it a spend cap.
- `DATABASE_URL_UNPOOLED` is the direct Neon URL from `docs/runbooks/neon.md` step 4.

Leave the `EMBED_MODEL` and `EMBED_DIMS` lines out unless you change them. They default to
`openrouter:openai/text-embedding-3-small` and 1536. (A line left empty, like `EMBED_DIMS=`, is ignored too.)
Never paste a key into chat or git.

## 2. Look before you spend (no cost, no network)
```
uv run python scripts/ingest.py --dry-run
```
It prints one line per page: how many chunks, and the smallest, average and largest chunk in tokens.
Expect an average of about 200 to 450 and a maximum under about 800. A page with one huge code block
can go over; that is on purpose, because a code block is never cut in half.

Add `--only fastapi-tutorial-body,pydantic-ai-core-concepts-agent` to try one or two pages first.

## 3. Ingest
```
uv run python scripts/ingest.py
```
The first run embeds every chunk. For the roughly 100 pages in the manifest that is a few hundred thousand
tokens, a few cents. Entries marked `kind: link` (pages we only link to) are skipped: they have no cached
file and are never embedded. Each page is written in one transaction, so if it stops (rate limit, no network) the pages already done
are kept: run the same command again and it carries on, because chunks that did not change are skipped.

## 4. Later: what changed?
After `fetch_docs.py` pulls newer pages, run:
```
uv run python scripts/ingest.py --check
```
It reads the database only. Each page shows `ok` or `CHANGED` with how many chunks it would embed and delete,
and the exit code is 1 if anything differs. Then run step 3 again: only the changed chunks cost anything.
It also lists stored pages that are no longer in the manifest (see the next step).

## 5. Remove pages that left the manifest
Ingesting never deletes a whole page: if you remove a source from `content/sources.yaml` (or turn it into
`kind: link`), its page and chunks stay in the database and would still show up in search. To clean up:
```
uv run python scripts/ingest.py --prune --dry-run
uv run python scripts/ingest.py --prune
```
The first command only lists what it would delete (`would delete  fastapi/some-page  (7 chunks)`). The second
deletes those pages and their chunks. `--prune` always looks at the whole manifest, so it cannot be combined
with `--only` or `--check`, and it refuses to run if the manifest lists nothing to keep.

## How it decides what to do
- A chunk's key is `sha256(source id | anchor | ordinal)`. It stays the same when the text is edited, so an
  edit updates the row in place.
- A chunk's hash is `sha256(text sent to the model + model name)`. A different hash means: embed again.
  Changing `EMBED_MODEL` therefore re-embeds everything by itself.
- A key that is in the database but no longer on the page is deleted.
- A page that is no longer in the manifest is not deleted by a normal run. That is what `--prune` is for.
- When a tiny section is merged into its neighbour, the neighbour with more text owns the chunk's anchor
  and heading path, so the citation points at the heading above the real content.
- Before it embeds anything the script checks that `EMBED_DIMS` equals the size of the `chunks.embedding`
  column (1536). A model with another size needs a schema change first; the script stops and says so.

## If something goes wrong
| Message | What to do |
| --- | --- |
| `cached page(s) missing` | Run the `fetch_docs.py` command it prints. |
| `set OPENROUTER_API_KEY` / `set DATABASE_URL_UNPOOLED` | Add it to the local env file, save, run again. |
| `the tables are missing` | Run `uv run python scripts/migrate.py`. |
| `EMBED_DIMS is ... but chunks.embedding is vector(...)` | The model's vector size does not fit the column. Use a 1536-size model, or ask Claude for a migration. |
| A rate-limit or 5xx error after one retry | Wait a minute and run again. Finished pages are kept. |
