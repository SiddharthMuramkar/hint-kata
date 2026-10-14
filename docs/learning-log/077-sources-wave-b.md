This adds the 56 source pages that the 21 wave-B lessons (FA6-FA12, PA6-PA12, GH6-GH12) will cite, so every lesson has official docs to read and a footer to link to. Nothing about the lessons themselves changes yet. Read `content/sources.yaml` first (the new entries are at the end), then `scripts/fetch_docs.py` for the two new kinds.

New entries by kind (56 in total):

- `fastapi_raw`: 16 FastAPI pages, pinned to tag 0.143.0 (MIT).
- `pydantic_ai_md`: 13 Pydantic AI pages, version 2.56.0 (MIT).
- `github_article`: 10 GitHub Docs pages, each with its full canonical path (CC BY 4.0).
- `raw`: 9 pages fetched exactly as served. 3 are Model Context Protocol docs (CC BY 4.0, spec 2026-07-28). 4 are from `anthropics/claude-code-action` and 2 from `github/github-mcp-server`, each pinned to a commit (MIT).
- `link`: 8 Claude Code docs pages. They have no reuse licence, so they are title + url only and are never fetched, hashed or copied.

What changed in the script: `fetch_docs.py` knows a `raw` kind (download the URL, change nothing) and a `link` kind. `--update` and `--check` skip links and print them as `link`, not `MISSING`. `--check` now reads the cached bytes, so a file with Windows line endings cannot drift from its hash. A full `--check` on the filled cache prints `104 ok, 0 failed, 8 link-only`.

What changed in the tests: `sha256`, `fetch_url` and `fetched_at` are required for every kind except `link`, and a `link` entry must not have them. A new test checks that raw GitHub files are pinned to a full commit, never a branch. New unit tests cover the `raw` and `link` paths.

Pages the issues named that were already in the manifest were not added twice: the Agents and Testing pages from Pydantic AI, the dependencies-with-yield page from FastAPI, and seven GitHub pages from wave A (including the required status checks troubleshooting page).

One lesson learned: the page list in an issue is a hint, not an address. Short paths like `.../troubleshooting-required-status-checks` have to be matched against GitHub's page list, and the install guide for the GitHub MCP server is not where the issue said (`docs/installation-guides/install-claude.md`, not `docs/install-claude.md`). Check every URL for a 200 before you hash it. Also, the MCP docs pages start with a three-line note aimed at AI agents. The `raw` kind keeps pages as served, so that note stays in the cache. Treat it as noise when you write lessons.

Closes #77

🤖 Generated with [Claude Code](https://claude.com/claude-code)
