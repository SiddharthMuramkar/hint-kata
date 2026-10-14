This adds 29 new pages to the sources manifest so the next nine lessons (FA3–FA5, PA3–PA5, GH3–GH5) have official docs to quote and cite. FastAPI gets 12 pages (request bodies, responses and errors, path and query parameters), Pydantic AI gets 2 (message history and persistence), and GitHub Docs gets 15 (reviewing, merging, secrets and permissions). PA3 and PA4 needed no new pages: structured output is already in the Output page, and streaming is covered by the Agents and Output pages, so nothing separate exists to add. Every entry has the same shape and licence/attribution wording as the existing ones, and `fetch_docs.py --update` filled in the sha256 and fetch time for all of them, so `--check` passes offline. A new test checks that every entry has all the required fields and that ids are unique. Read `content/sources.yaml` first, then `tests/test_sources_manifest.py`.

Closes #42

🤖 Generated with [Claude Code](https://claude.com/claude-code)
