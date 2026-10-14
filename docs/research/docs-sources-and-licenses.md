# Documentation sources, licences and content inventory

_Research archive. Checked against primary sources on 2026-10-14. Facts about fast-moving tools (Claude Code, Pydantic AI, FastAPI, GitHub, OpenRouter) go stale quickly: re-check before relying on a number._

- **Needed by:** Phase 1 (6 lessons) and Phase 2 (full ingestion)
- **Licence / attribution notes:** FastAPI docs: MIT (© 2018 Sebastián Ramírez; FastAPI is a registered trademark). Pydantic AI docs: MIT (© Pydantic Services Inc.). GitHub Docs: CC-BY-4.0 (attribution + link + 'modified'). Claude Code docs: no reuse licence found (all rights reserved) → link and summarise only. MCP docs: CC-BY-4.0. claude-code-action and github-mcp-server: MIT.
- **Covers:** where each doc set lives as Markdown, its syntax quirks, pinning, licences, attribution text, and a 12-lesson inventory per track

## FastAPI as a content source (docs Markdown, include syntax, license, version pinning) and as the runtime (current CLI, lifespan, deps, settings, DB, testing, SSE, FastAPI Cloud, Vercel), plus a 12-lesson track

**Summary.** The latest FastAPI release is 0.143.0, published 2026-10-08. Its tag points at commit f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007, which was also master HEAD when I checked. Releases come out very often: 57 on PyPI so far in 2026, with a new minor version every 3-6 weeks, and a minor version can break things (0.137 did, and so did 0.143). Since the docs site has no version selector, pin ingestion to a tag or commit SHA and pin the app to `>=0.143.0,<0.144.0`. The English docs in `docs/en/docs` are 156 Markdown files, about 1,455 KB. About 695 KB of that is `release-notes.md`, and the parts a learner needs (tutorial, advanced, deployment, how-to, plus CLI, Python types and async pages) come to 115 files, about 701 KB and 99k words. On top of that, 292 example files from `docs_src/` are pulled in through 443 `{* ../../docs_src/... ln[..] hl[..] *}` includes. Those includes are expanded by tiangolo's own `markdown-include-variants` package, which calls itself internal-use only. The rule is simple to copy: the path is relative to `docs/en/`, `ln` takes 1-based inclusive line ranges, and `hl` only sets highlighting. Other syntax a renderer must handle: `///` admonition blocks, `//// tab |` tabs, explicit `{ #anchor }` heading IDs (these match the live site anchors, so they work for deep-link citations), terminal-demo `<div class="termy">` HTML and Mermaid diagrams. The API reference pages are empty `::: fastapi.X` stubs whose content comes from code docstrings. There is no llms.txt: it returns 404, and the pull request that tried to add one was closed without merging. The repo is MIT-licensed, copyright Sebastián Ramírez, and the license covers the "associated documentation files", so keep the copyright notice and license text with any reused docs. The FastAPI trademark is registered, so don't use the logo or suggest the site is official. For the runtime: Python 3.10+ and Pydantic v2 only; `fastapi dev`/`fastapi run` with `[tool.fastapi] entrypoint`; `lifespan` replaces the deprecated startup/shutdown events, yet the SQL tutorial's example code still uses `on_event`; `Depends(scope=...)`; pydantic-settings; SQLModel is the only database library the docs teach, and they never mention asyncpg, psycopg, pgvector or Vercel; built-in Server-Sent Events (SSE) support (`fastapi.sse.EventSourceResponse`) has existed since 0.135.0. Vercel deploys FastAPI with no configuration through its own `[tool.vercel] entrypoint` setting. FastAPI Cloud is in public beta, with a free Hobby plan and a Pro plan at $20 per seat per month.

### Findings

- **Latest FastAPI is 0.143.0, released 2026-10-08 (GitHub release 12:29:29Z; PyPI upload 12:29:44). Its tag SHA is f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007, which equalled master HEAD (committed 2026-10-08T12:25:54Z) when checked on 2026-10-14.** [high, load-bearing]
  Verified with gh api repos/fastapi/fastapi/releases, git/ref/tags/0.143.0 and https://pypi.org/pypi/fastapi/json. Related latest versions: fastapi-cli 0.0.32 (2026-07-16), fastapi-cloud-cli 0.26.0, sqlmodel 0.0.48, pydantic 2.14.1, pydantic-settings 2.15.0, starlette 1.8.0, pgvector 0.5.1.
  Source: <https://github.com/fastapi/fastapi/releases/tag/0.143.0>
- **Releases are very frequent, and minor versions can break things. PyPI shows 57 releases in 2026 so far. Minor versions so far: 0.135.0 on Mar 1, 0.136 Apr 16, 0.137 Jun 14, 0.138 Jun 20, 0.139 Jul 1, 0.140 Jul 24, 0.141 Jul 29, 0.142 Sep 29, 0.143 Oct 8. The docs' own versions page says to pin like `fastapi[standard]>=0.112.0,<0.113.0`, because breaking changes and new features land in MINOR releases.** [high, load-bearing]
  0.137.0 broke code that treats router.routes as a list: it is now a tree, and routes added after include_router are now picked up. 0.143.0 made automatic OpenTelemetry exporter setup opt-in, via FASTAPI_OTEL_AUTO_CONFIGURE=true or FastAPI(telemetry={"auto_configure": True}). The versions page also says not to pin starlette, and to pin pydantic loosely (e.g. >=2.7.0,<3.0.0).
  Source: <https://github.com/fastapi/fastapi/blob/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007/docs/en/docs/deployment/versions.md>
- **Size of the English docs at the 0.143.0 SHA, from git tree blob sizes (KB = bytes/1024): docs/en/docs has 156 .md files, 1,454.5 KB. release-notes.md alone is 694.7 KB. By section: tutorial 51 files/310.9 KB, advanced 35/173.0 KB, deployment 9/83.0 KB, how-to 12/39.1 KB, reference 24/18.0 KB (stubs only), root pages 22/830 KB (including release notes). The core learning set (tutorial, advanced, deployment, how-to, fastapi-cli, python-types, async, index, features, environment-variables, virtual-environments, editor-support) is 115 files, about 701 KB, about 99k words.** [high]
  The tree was not truncated (3,618 entries). docs_src/ has 467 files, 211 KB, and 292 unique docs_src files are referenced from English docs. The core set is roughly 150-200k tokens before code includes are expanded. That is cheap to embed, but the included code should be expanded before chunking.
  Source: <https://api.github.com/repos/fastapi/fastapi/git/trees/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007?recursive=1>
- **The `{* path [ln[..]] [hl[..]] [title[".."]] *}` syntax is handled by the `markdown_include_variants` Python-Markdown extension (tiangolo/markdown-include-variants 0.0.8, MIT, which labels itself 'Internal Project ... no guarantees'). It is matched by the regex `^\{\*\s*(\S+)\s*(.*)\*\}$` and must be on a line of its own. It expands into mdx_include `{!path[ln:a-b]!}` directives inside a ```python fence wrapped in a `//// tab | Python 3.10+` block.** [high, load-bearing]
  Resolution rules from the source code. ln takes comma-separated, 1-based, inclusive ranges (`3:6,8`). The expansion inserts `# Code above omitted 👆`, `# Code here omitted 👈` and `# Code below omitted 👇`, and adds a collapsed '👀 Full file preview'. hl uses line numbers from the source file and is remapped to the rendered block. ln[0] produces only the preview. The given path is the preferred variant; sibling `_an`/`_pyXY` files go into a collapsed 'Other versions and variants' block, and today only `_py310` and `_an_py310` files exist. In FastAPI the paths look like `../../docs_src/...` relative to `docs/en/` (the mkdocs.yml directory), so they resolve to repo-root `docs_src/`. There are 443 such includes in the English docs: 427 use hl and 48 use ln. One include, in reference/openapi docs, points at `../../fastapi/openapi/docs.py` instead of docs_src.
  Source: <https://github.com/tiangolo/markdown-include-variants/blob/HEAD/src/markdown_include_variants/_main.py>
- **The older mdx_include syntax also appears 6 times, inside fenced code blocks: `{!../../docs_src/...!}` and `{!> path!}` (the `>` means apply the include line's indentation). It is used in python-types.md, advanced/templates.md (HTML/CSS) and advanced/generate-clients.md (JS).** [high, load-bearing]
  mdx-include 1.4.2 syntax: `{!recurs_state apply_indent file_path [ln:slice] | encoding !}`. A renderer should resolve these along with `{*`, or the code samples in those pages will be missing.
  Source: <https://pypi.org/project/mdx-include/>
- **Other Markdown syntax used in the English docs. pymdownx.blocks admonitions (counts): `/// tip` 171, `/// note` 124, `/// note | Title` 49, `/// warning` 31, `/// tip | Title` 19, `/// danger` 5, `/// details | Title` 4, closed by `///`. Tab blocks use four slashes: `//// tab | Title` 38 times (labels like 'Python 3.10+', 'Test', 'Info'). 1,117 headings carry explicit `{ #anchor }` IDs. There are 50 `<div class="termy">` terminal demos containing raw `<font>`/`<span>` HTML, 11 ```mermaid fences, 42 `<abbr title>` and 49 `<dfn title>` tags. Reference pages are 61 `::: fastapi.X` mkdocstrings directives with no prose in the Markdown.** [high, load-bearing]
  mkdocs.yml enables pymdownx.blocks.admonition (types note, attention, caution, danger, error, tip, hint, warning, info, check), pymdownx.blocks.details, pymdownx.blocks.tab (alternate_style), mdx_include, markdown_include_variants and zensical.extensions.macros. Jinja `{% %}`/`{{ }}` macros appear only in 4 non-learning pages such as fastapi-people.md. Anchor IDs match the live site: I verified `#resuming-with-last-event-id` and `#sse-with-post` on /tutorial/server-sent-events/.
  Source: <https://github.com/fastapi/fastapi/blob/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007/docs/en/mkdocs.yml>
- **The FastAPI docs site is now built with Zensical (zensical>=0.0.42 in the docs dependency group), run from scripts/docs.py with `zensical build --config-file ...`. It is not plain MkDocs Material any more.** [high]
  The docs group also pins markdown-include-variants>=0.0.8, mdx-include>=1.4.1,<2.0.0 and mkdocstrings[python]>=1.0.3. Reproducing the official build is heavy; a small custom preprocessor is the more practical option.
  Source: <https://github.com/fastapi/fastapi/blob/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007/pyproject.toml>
- **fastapi.tiangolo.com has no llms.txt: /llms.txt, /llms-full.txt and per-page `index.md` URLs all returned 404 on 2026-10-14. PR #13977, which would have added llms.txt, was closed unmerged on 2025-08-31; the maintainer said it would need to be autogenerated and 'I'll pass on this for now'.** [high, load-bearing]
  https://fastapi.tiangolo.com/sitemap.xml exists and lists 152 English URLs. Pages map as `docs/en/docs/<p>.md` to `https://fastapi.tiangolo.com/<p>/`, with `index.md` mapping to its directory (verified for /tutorial/dependencies/ and /learn/). robots.txt holds only a Cloudflare content-signals comment preamble with no directives. The site also loads a Kapa.ai widget (js/init_kapa_widget.js).
  Source: <https://github.com/fastapi/fastapi/pull/13977>
- **License: the repo LICENSE is MIT, 'Copyright (c) 2018 Sebastián Ramírez'. It grants rights to 'this software and associated documentation files' on condition that 'the above copyright notice and this permission notice shall be included in all copies or substantial portions'. pyproject declares license = "MIT".** [medium, load-bearing]
  The license text is certain. That MIT covers the docs prose is an inference, though a strong one: the docs live in the same repo and the docs have no separate license. Reusing or adapting docs text and code samples needs the copyright line and the MIT text, for example on a licenses page with a link from each lesson.
  Source: <https://github.com/fastapi/fastapi/blob/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007/LICENSE>
- **Trademark: the docs footer partial says 'The FastAPI trademark is owned by @tiangolo and is registered in the US and across other regions.' MIT grants no trademark rights.** [high, load-bearing]
  Using the name to describe the topic is fine. Avoid the FastAPI logo and anything that suggests official or affiliated status.
  Source: <https://github.com/fastapi/fastapi/blob/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007/docs/en/overrides/partials/copyright.html>
- **Runtime baseline: requires-python >=3.10; dependencies are starlette>=0.46.0, pydantic>=2.9.0 (Pydantic v1 dropped), typing-extensions, typing-inspection, annotated-doc and opentelemetry-api>=1.44.0. The `standard` extra adds fastapi-cli[standard]>=0.0.32, uvicorn[standard], httpx, jinja2, python-multipart, email-validator, pydantic-settings, pydantic-extra-types, opentelemetry-sdk, the OTLP exporter and fastar. A `standard-no-fastapi-cloud-cli` extra also exists.** [high, load-bearing]
  Classifiers list Python 3.10-3.14, and 0.136.0 added support for free-threaded 3.14t. docs_src now contains only `_py310` and `_an_py310` example variants.
  Source: <https://github.com/fastapi/fastapi/blob/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007/pyproject.toml>
- **CLI: `fastapi dev` auto-reloads, binds 127.0.0.1 and sets FASTAPI_ENV=development if it is unset. `fastapi run` has no reload, binds 0.0.0.0 and leaves FASTAPI_ENV unchanged. The recommended entrypoint config is `[tool.fastapi] entrypoint = "main:app"` in pyproject.toml. Alternatives are `fastapi dev main.py` and `fastapi dev --entrypoint main:app`; the docs prefer pyproject because the VS Code extension and FastAPI Cloud read it.** [high, load-bearing]
  The tutorial now installs with uv first: `uv init awesome-project --bare`, `uv add "fastapi[standard]"`, `uv run fastapi dev` (https://fastapi.tiangolo.com/tutorial/).
  Source: <https://fastapi.tiangolo.com/fastapi-cli/>
- **Lifespan: the recommended pattern is `FastAPI(lifespan=lifespan)` with an `@asynccontextmanager` function that yields. The `startup`/`shutdown` events are documented as deprecated, and it is 'all lifespan or all events, not both'. Lifespan runs only for the main app, not mounted sub-apps. Even so, the SQL tutorial's example code still uses `@app.on_event("startup")` (docs_src/sql_databases/tutorial001_an_py310.py, line 35).** [high]
  Testing: wrapping TestClient in `with` runs lifespan (/advanced/testing-events/). httpx AsyncClient does not trigger lifespan, and the docs point to asgi-lifespan's LifespanManager (/advanced/async-tests/). The on_event mismatch makes a good 'think deeper' question.
  Source: <https://fastapi.tiangolo.com/advanced/events/>
- **Dependencies: the docs and the bundled agent skill both prescribe `Annotated[T, Depends(fn)]` with reusable type aliases (e.g. `SessionDep`). `Depends(scope="function" | "request")` was added in 0.121.0. Dependencies that use yield default to "request", where exit code runs after the response is sent; "function" closes them before the response is sent.** [high]
  This matters for SSE tutor streams that use a DB session from a dependency. With the default request scope the session stays open for the whole stream. A dependency with request scope cannot depend on one with function scope.
  Source: <https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-with-yield/>
- **Settings: the docs use pydantic-settings `BaseSettings` with `model_config = SettingsConfigDict(env_file=".env")`, provided through a `@lru_cache`'d `get_settings()` dependency so tests can override it.** [high]
  Example file: docs_src/settings/app03_an_py310/config.py.
  Source: <https://fastapi.tiangolo.com/advanced/settings/>
- **Database guidance: the FastAPI docs teach only SQLModel. The example is synchronous with SQLite, uses a session-per-request yield dependency, calls `SQLModel.metadata.create_all` at startup, and recommends Alembic for migrations. The English docs never mention asyncpg, psycopg, pgvector or Vercel. how-to/testing-database.md just points to the SQLModel docs. The bundled skill says to prefer SQLModel over SQLAlchemy.** [high]
  pgvector-python 0.5.1 supports SQLModel (`Field(sa_type=VECTOR(n))` from pgvector.sqlalchemy), Psycopg 3 (`register_vector`, `register_vector_async`, and pool `configure=`), and asyncpg (`register_vector`, pool `init=`). Source: https://github.com/pgvector/pgvector-python. A Postgres/pgvector lesson would need material beyond the FastAPI docs.
  Source: <https://fastapi.tiangolo.com/tutorial/sql-databases/>
- **Testing: TestClient is based on HTTPX and works in plain `def` pytest tests. Async tests use `@pytest.mark.anyio` with `AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`. `app.dependency_overrides` swaps out dependencies.** [high]
  See also /tutorial/testing/ and /advanced/testing-dependencies/.
  Source: <https://fastapi.tiangolo.com/advanced/async-tests/>
- **Built-in streaming: JSON Lines arrived in 0.134.0 (`yield` in a path operation produces application/jsonl), and Server-Sent Events in 0.135.0. For SSE: `from fastapi.sse import EventSourceResponse, ServerSentEvent`, set `response_class=EventSourceResponse` and `yield`. A return type of `AsyncIterable[Item]` turns on Pydantic validation and serialization. `ServerSentEvent` supports event, id, retry, comment, and data or raw_data (only one of those two). Clients can resume with the Last-Event-ID header, and POST works too. FastAPI automatically sends a keep-alive ping every 15s and sets Cache-Control: no-cache and X-Accel-Buffering: no.** [high, load-bearing]
  This fits the tutor chat directly. LLMs trained before 2026 won't know this API, which is a good showcase for answering from the docs with citations. Binary streaming is covered at /advanced/stream-data/.
  Source: <https://fastapi.tiangolo.com/tutorial/server-sent-events/>
- **Other recent features: `app.frontend("/", directory="dist")` / `router.frontend()` (0.138.0), dependencies on frontend routes (0.139.0), `check_dir="auto"` (0.141.0), and native OpenTelemetry traces, metrics and logs (0.142.0).** [high]
  Vercel serves app.frontend()/StaticFiles from its CDN at build time, except where middleware or Depends guards apply.
  Source: <https://fastapi.tiangolo.com/tutorial/frontend/>
- **FastAPI ships an official agent skill inside the package, at fastapi/.agents/skills/fastapi/SKILL.md plus references for dependencies, streaming, pydantic, responses, path-operations and other-tools. The tutorial says to install it with `uvx library-skills` and, for Claude Code, to 'select `.claude/skills` when asked where to install the skill'.** [high]
  The skill's conventions: use Annotated; don't use `...` (Ellipsis) defaults; prefer return types over response_model; configure the entrypoint in pyproject; use uv, Ruff and ty; Asyncer over run_in_threadpool; SQLModel; HTTPX. This makes a concrete example for Track 3 (Claude Code + skills in a GitHub flow).
  Source: <https://fastapi.tiangolo.com/tutorial/#ai-agent-skills>
- **FastAPI Cloud is the hosting service from the FastAPI author's team and the project's primary sponsor; you deploy with `uv run fastapi deploy`. It is in public beta. The pricing page lists 'Public beta pricing': Hobby is $0 (3 apps, 1 custom domain, 0.1 vCPU/512 MB shared bursting to 0.5 vCPU, scale-to-zero, 1-day logs and metrics). Pro is $20 per seat per month (25 apps, 20 custom domains, 10 replicas, 10 team members, 14-day retention). Usage-based billing is not invoiced yet.** [medium, load-bearing]
  Beta pricing is likely to change. The page contradicts itself on Hobby replicas (3 in the plan description, 2 in the comparison table). The docs page is https://fastapi.tiangolo.com/deployment/fastapicloud/.
  Source: <https://fastapicloud.com/pricing>
- **The FastAPI docs say nothing about Vercel; deployment/cloud.md lists only FastAPI Cloud and the sponsor Railway. Vercel's own docs cover FastAPI with zero config: Vercel looks for `app` in app.py, index.py, server.py, main.py, wsgi.py or asgi.py, also inside src/ or app/, or wherever `[tool.vercel] entrypoint = "module:app"` points (legacy `[project.scripts] app = ...` still works). The app runs as a single Vercel Function on Fluid compute. Lifespan is supported, but shutdown cleanup is capped at 500ms after SIGTERM. Streaming works on the Python runtime. Python 3.12 is the default, with 3.13 and 3.14 available. Bundles are limited to 500 MB, a `public/` directory is served from the CDN, and maxDuration is set in vercel.json under functions keyed by the entrypoint file.** [high, load-bearing]
  Python runtime page: https://vercel.com/docs/functions/runtimes/python (last updated 2026-08-12). Build hook: `[tool.vercel.scripts] build = "..."`. Static options live under `[tool.vercel.fastapi.static]` (cdn, exclude). `[tool.fastapi]` and `[tool.vercel]` are separate keys and both should point to the same app.
  Source: <https://vercel.com/docs/frameworks/backend/fastapi>

### Exact snippets (copied from the sources named)

**FastAPI CLI entrypoint (pyproject.toml)** — <https://fastapi.tiangolo.com/fastapi-cli/>

```toml
[tool.fastapi]
entrypoint = "main:app"
```

**Vercel FastAPI entrypoint (pyproject.toml)** — <https://vercel.com/docs/frameworks/backend/fastapi>

```toml
[tool.vercel]
entrypoint = "backend.server:app"
```

**Docs code-include syntax as used in FastAPI Markdown (resolve ../../docs_src relative to docs/en/)** — <https://github.com/fastapi/fastapi/blob/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007/docs/en/docs/tutorial/server-sent-events.md>

```markdown
{* ../../docs_src/server_sent_events/tutorial001_py310.py ln[1:25] hl[4,22] *}
```

**FastAPI docs markdown_extensions (blocks, tabs, includes) excerpt** — <https://github.com/fastapi/fastapi/blob/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007/docs/en/mkdocs.yml>

```yaml
  pymdownx.blocks.admonition:
    # TODO: remove types section (with custom types) once translations are migrated to
    # not use custom types too
    types:
    # Default types
    - note
    - attention
    - caution
    - danger
    - error
    - tip
    - hint
    - warning
    # Custom types
    - info
    - check
  pymdownx.blocks.details: null
  pymdownx.blocks.tab:
    alternate_style: true
  mdx_include: null
  markdown_include_variants: null
```

**Built-in SSE endpoint (docs_src/server_sent_events/tutorial001_py310.py, excerpt)** — <https://github.com/fastapi/fastapi/blob/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007/docs_src/server_sent_events/tutorial001_py310.py>

```python
from collections.abc import AsyncIterable, Iterable

from fastapi import FastAPI
from fastapi.sse import EventSourceResponse
from pydantic import BaseModel

app = FastAPI()


class Item(BaseModel):
    name: str
    description: str | None


items = [
    Item(name="Plumbus", description="A multi-purpose household device."),
    Item(name="Portal Gun", description="A portal opening device."),
    Item(name="Meeseeks Box", description="A box that summons a Meeseeks."),
]


@app.get("/items/stream", response_class=EventSourceResponse)
async def sse_items() -> AsyncIterable[Item]:
    for item in items:
        yield item
```

**Version pin pattern from FastAPI docs (adapt to >=0.143.0,<0.144.0)** — <https://fastapi.tiangolo.com/deployment/versions/>

```text
fastapi[standard]>=0.112.0,<0.113.0
```

**Vercel function maxDuration for a FastAPI entrypoint (vercel.json)** — <https://vercel.com/docs/frameworks/backend/fastapi>

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "app/main.py": {
      "maxDuration": 60
    }
  }
}
```

**pgvector with Psycopg 3 connection pool** — <https://github.com/pgvector/pgvector-python>

```python
def configure(conn):
    register_vector(conn)

pool = ConnectionPool(..., configure=configure)
```

### Recommendations
- Ingest docs from GitHub, not the website. Pin a tag or SHA (0.143.0 = f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007) and read files from raw.githubusercontent.com at that SHA. Map `docs/en/docs/<p>.md` to `https://fastapi.tiangolo.com/<p>/` (`index.md` maps to its directory) and add `#<anchor>` from each heading's `{ #anchor }` so citations deep-link. Store source path, SHA and heading path as metadata on every chunk.
- Write a small, tested preprocessor instead of reproducing the Zensical build. Resolve `{* path ln[..] *}` by reading `docs_src/<path minus ../../>` and keeping only the ln ranges (drop hl and the other variants). Resolve `{!path!}` and `{!> path!}` the same way. Turn `/// type | title ... ///` and `//// tab | title ... ////` blocks into labeled sections. Strip the HTML out of `<div class="termy">` blocks, keep mermaid as code, and fail CI if any `{*` or `{!` is left unresolved.
- Leave out of the tutor corpus: release-notes.md (or index it separately for 'what changed' questions), _llm-test.md, translation-banner, fastapi-people, management, newsletter, contributing, translations, external-links, and the empty reference/ stubs. Add the reference content later by extracting docstrings with griffe if it's needed.
- Attribution: give each FastAPI lesson a footer like 'Adapted from the FastAPI documentation, © 2018 Sebastián Ramírez, MIT License' linking to the source page, and add a /licenses page with the full MIT text. Say clearly that the site is not affiliated with FastAPI, and don't use the logo.
- Scheduled re-sync: a weekly GitHub Action reads the latest release tag through the GitHub API. If the tag changed, it diffs the docs/en/docs and docs_src files between the old and new SHA, re-embeds only the changed chunks, and opens a PR that bumps the pinned SHA so a human reviews it. Pin the app itself to `fastapi>=0.143.0,<0.144.0` and use the same PR flow, gated on tests, for upgrades.
- Runtime choices for the site backend: set both `[tool.fastapi] entrypoint` and `[tool.vercel] entrypoint` to the same `module:app`. Create Pydantic AI agents and clients in `lifespan`. Stream the tutor with `EventSourceResponse` and an `AsyncIterable[...]` return type. Use `Depends(scope="function")` for DB sessions that aren't needed while a stream is running. Production on Vercel doesn't need `fastapi[standard]`'s cloud CLI or OTel SDK, so consider plain `fastapi` plus the specific extras you use, or `standard-no-fastapi-cloud-cli`.
- Proposed 12-lesson FastAPI track, built around the mental models behind 'it didn't stick'. L1 Run it right: uv, `fastapi dev`/`fastapi run` and entrypoints (/tutorial/, /fastapi-cli/, /tutorial/first-steps/). L2 Types drive validation: path and query params with Annotated (/python-types/, /tutorial/path-params/, /tutorial/query-params/, /tutorial/query-params-str-validations/, /tutorial/path-params-numeric-validations/). L3 Request bodies with Pydantic v2 (/tutorial/body/, /tutorial/body-multiple-params/, /tutorial/body-nested-models/, /tutorial/body-fields/). L4 Response models, status codes and errors (/tutorial/response-model/, /tutorial/extra-models/, /tutorial/response-status-code/, /tutorial/handling-errors/). L5 async def vs def (/async/). L6 Dependency injection (/tutorial/dependencies/, /tutorial/dependencies/classes-as-dependencies/, /tutorial/dependencies/sub-dependencies/, /tutorial/dependencies/global-dependencies/). L7 Resource lifecycles: yield dependencies, scope, lifespan (/tutorial/dependencies/dependencies-with-yield/, /advanced/advanced-dependencies/, /advanced/events/). L8 Settings and secrets (/environment-variables/, /advanced/settings/). L9 Databases: session per request (/tutorial/sql-databases/, plus a psycopg 3/pgvector supplement). L10 Bigger apps with APIRouter (/tutorial/bigger-applications/, /tutorial/path-operation-configuration/, /tutorial/metadata/). L11 Testing (/tutorial/testing/, /advanced/testing-dependencies/, /advanced/testing-events/, /advanced/async-tests/). L12 Streaming: SSE and JSON Lines, plus deploy notes (/tutorial/server-sent-events/, /tutorial/stream-json-lines/, /deployment/versions/, /deployment/concepts/, plus Vercel's FastAPI page).
- Best 3 for the first release: L1 (Run it right), L6 (Dependency injection), L12 (SSE streaming). L1 checks the whole hands-on pipeline on a low-RAM Mac with no DB. L6 is the concept most likely to be why 'it didn't stick', and it has plenty of quiz and rubric material. L12 is new (0.135+), so the tutor's citations add clear value over model memory, and it mirrors how the site's own tutor chat works. The source pages are small (about 6-14 KB each), which makes the docs-chat RAG easy to test. Swap in L11 (Testing) if hands-on tasks will be checked with pytest.
- Use the SQL tutorial's leftover `on_event` call and the change of lifespan defaults as 'think deeper' prompts. Use the bundled FastAPI agent skill (`uvx library-skills` into `.claude/skills`) as a cross-link to Track 3.

### Risks
- Docs are unversioned, while the code ships breaking minor releases (0.137 router tree, 0.143 OTel opt-in). Citations to the live site can drift away from the pinned content you indexed. Mitigation: re-sync and diff, and optionally cite pinned GitHub blob URLs as a fallback.
- markdown-include-variants calls itself an internal project with 'no guarantees'. The include syntax or variant naming can change without notice (it already went from multi-version to only `_py310`), so the preprocessor needs fail-loud tests.
- Reference pages are empty mkdocstrings stubs in the Markdown. A RAG built only from Markdown will lack API parameter-level detail.
- The tutor and grader models' built-in knowledge predates SSE (0.135), app.frontend (0.138), Depends(scope) (0.121), native OTel (0.142) and the 0.143 OTel opt-in. Rubrics must be anchored to the retrieved docs, or the grader may mark correct modern answers as wrong.
- The docs' database path (sync SQLModel with SQLite) doesn't match the site's stack (Postgres/pgvector on Neon with psycopg 3 or asyncpg). Lessons will need supplementary material that has no official FastAPI citation.
- Vercel limits: shutdown cleanup in lifespan is capped at 500ms. Long SSE tutor streams are bounded by the function's maxDuration. `fastapi[standard]` pulls in the OTel SDK and cloud CLI, which bloat the bundle and cold starts.
- Beta prices and limits for FastAPI Cloud (Hobby $0, Pro $20 per seat) may change, and the pricing page contradicts itself on Hobby replicas, so don't hardcode them in lesson content.
- That the MIT license covers the docs prose is an inference: the docs have no separate license. Skipping attribution would breach MIT's notice condition. Using the logo or implying official status could raise trademark issues.

### Open questions
- What are the default and maximum maxDuration on Vercel's Hobby and Pro plans for Python functions under Fluid compute, and is that long enough for SSE tutor streams? (Not checked here.)
- Should tutor citations point to the live fastapi.tiangolo.com URLs, which are nicer but can drift, or to pinned GitHub blob URLs, which are exact but less readable? Or both?
- For the backend's own database access: SQLModel, matching the docs and the skill, or psycopg 3 / asyncpg with pgvector, matching the RAG workload? This affects how closely L9 can follow the official docs.
- Will learners' hands-on tasks run locally with uv, which is fine on low RAM, or be checked server-side, for example by running pytest in GitHub Actions? This decides whether L11 Testing belongs in the first release.
- Should release-notes.md (695 KB) be indexed so the tutor can answer 'what changed in version X' questions, or left out to keep retrieval focused?
- markdown-include-variants' README says the path points to the 'simplest version', but its code treats the given path as the preferred variant. I followed the code, but confirm against a rendered page if variant handling matters.

### Fact-check (second agent re-read the sources)

I checked everything against the source at tag SHA f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007 (pulled through codeload into memory), the GitHub API, the PyPI JSON API and the live sites (curl). Three claims need corrections. (a) The list of 2026 minor versions leaves out 0.129-0.134. (b) The include that is not under docs_src is in how-to/configure-swagger-ui.md, not the reference/openapi docs. (c) There are 12 mermaid fences in total (11 without release-notes.md). Jinja also appears in advanced/templates.md, a learning page, as {% raw %} blocks, so a renderer must strip or handle {% raw %}/{% endraw %}. The docs are built with Zensical (`zensical build`, cwd = the staged lang config directory) using mkdocs.yml. The Vercel FastAPI page links to an app.frontend() API at fastapi.tiangolo.com/tutorial/frontend/, which I did not verify. The only file written was a temporary copy of markdown-include-variants _main.py in the session scratchpad: (session scratchpad)

Corrections:
- [corrected] 57 PyPI releases in 2026. 2026 minor versions: 0.135 Mar 1, 0.136 Apr 16, 0.137 Jun 14, 0.138 Jun 20, 0.139 Jul 1, 0.140 Jul 24, 0.141 Jul 29, 0.142 Sep 29, 0.143 Oct 8. versions.md pins like fastapi[standard]>=0.112.0,<0.113.0 because breaking changes land in MINOR releases. 0.137.0 made router.routes a tree; 0.143.0 made OTel auto-configure opt-in. Don't pin starlette; pin pydantic loosely. → The count of 57 releases in 2026 is right, and the listed dates are right. The 'minor versions so far' list is incomplete. It leaves out six earlier 2026 minor versions: 0.129.0 (Feb 12), 0.130.0 and 0.131.0 (Feb 22), 0.132.0 (Feb 23), 0.133.0 (Feb 24) and 0.134.0 (Feb 27). So 2026 has 15 minor bumps, not 9. The rest checks out: the versions.md text (pin pattern, 'Breaking changes and new features are added in MINOR versions', don't pin starlette, pydantic>=2.7.0,<3.0.0), the 0.137.0 router.routes tree change and the 0.143.0 FASTAPI_OTEL_AUTO_CONFIGURE / telemetry={'auto_configure': True} change all match the release notes. (<https://pypi.org/pypi/fastapi/json>)
- [corrected] The {* path ln[..] hl[..] title[..] *} syntax is handled by markdown_include_variants 0.0.8 (MIT, 'Internal Project … no guarantees'). Regex ^\{\*\s*(\S+)\s*(.*)\*\}$. It expands into mdx_include {!path[ln:a-b]!} inside a python fence in a //// tab block. Counts: 443 includes, 427 use hl, 48 use ln. One include, in reference/openapi docs, points at ../../fastapi/openapi/docs.py. → The one include that is not under docs_src is in docs/en/docs/how-to/configure-swagger-ui.md (`{* ../../fastapi/openapi/docs.py ln[9:24] hl[18:24] *}`), not in the reference/openapi docs. Everything else matches the source and the docs at the tag: the regex, ln parsing (1-based, inclusive, comma-separated), the omitted-code markers, the 'Full file preview' and 'Other versions and variants' details blocks, ln[0] giving only the preview, and the counts 443/427/48. docs_src does contain only _py310 and _an_py310 variants (the unsuffixed files are __init__.py or sit inside suffixed folders). Three small points: without ln the expansion is `{!path!}` with no slice; hl is remapped only when ln is present; and the tab label is the variant's title, which can be 'Python 3.10+ - non-Annotated'. Path() resolves against the build CWD. That CWD is the staged docs/en config directory (scripts/docs.py runs `zensical build` with cwd set to the config's parent), so ../../docs_src still lands on repo-root docs_src. (<https://github.com/tiangolo/markdown-include-variants/blob/HEAD/src/markdown_include_variants/_main.py>)
- [corrected] Admonition counts (tip 171, note 124, note|Title 49, warning 31, tip|Title 19, danger 5, details|Title 4), 38 //// tab blocks, 1,117 { #anchor } headings, 50 termy divs, 11 mermaid fences, 42 abbr, 49 dfn, 61 ::: fastapi.X directives. mkdocs.yml extensions as listed. Jinja appears only in 4 non-learning pages such as fastapi-people.md. → Three corrections. (1) There are 12 mermaid fences in docs/en/docs, or 11 if release-notes.md is left out. (2) Jinja appears in 4 pages: index.md, external-links.md, fastapi-people.md and advanced/templates.md. templates.md is a learning page and wraps its Jinja examples in {% raw %}…{% endraw %}, so a renderer has to handle {% raw %}. (3) The admonition list leaves out one `/// Note` (capital N) and one `/// warning | Title`. All other counts match: the admonition and tab counts, 1,117 anchors, 50 termy, 42 abbr, 49 dfn and 61 mkdocstrings directives. The listed extensions (including zensical.extensions.macros and the superfences mermaid custom fence), js/init_kapa_widget.js and the live anchors #resuming-with-last-event-id and #sse-with-post are all present. The site is built with `zensical build` using this mkdocs.yml. (<https://github.com/fastapi/fastapi/blob/f5c6e9b4f9cadc1bf0f9a1fd672e621206b63007/docs/en/mkdocs.yml>)

Snippet checks:
- FastAPI CLI entrypoint (pyproject.toml): none. It matches fastapi-cli.md lines 66-67 exactly.
- Vercel FastAPI entrypoint (pyproject.toml): none. It matches the Vercel FastAPI docs exactly.
- Docs code-include syntax: none. It matches server-sent-events.md line 42 exactly. Path() resolves against the build CWD, which is the docs/en config directory (staged).
- FastAPI docs markdown_extensions excerpt: none. It matches mkdocs.yml verbatim, comments included. Being an excerpt, it leaves out zensical.extensions.macros, the superfences mermaid custom_fence, abbr, attr_list, md_in_html, toc and the other pymdownx extensions, which a renderer also needs.
- Built-in SSE endpoint: none in content, since it matches tutorial001_py310.py lines 1-25 verbatim. Minor: `Iterable` is imported but unused in this excerpt (it is used by line 29 of the full file), so linters will flag it if the excerpt is used on its own.
- Version pin pattern: none. It matches versions.md line 28 verbatim.
- Vercel function maxDuration (vercel.json): none. It matches the Vercel FastAPI docs verbatim. The functions key must be the resolved entrypoint file path.
- pgvector with Psycopg 3 connection pool: none. It matches the pgvector-python README verbatim. Note that it needs `from pgvector.psycopg import register_vector` and `from psycopg_pool import ConnectionPool` (not shown), and `...` stands for the conninfo/args. For async the README says to use register_vector_async.

## Content sources for track 3 "GitHub for the Claude Code era": GitHub Docs (rendering, LLM endpoints, license, page paths), Claude Code docs and claude-code-action reuse terms, MCP docs and github-mcp-server licenses, plus a 12-lesson outline

**Summary.** GitHub Docs is the easiest source to ingest. docs.github.com/llms.txt is live and points LLM tools to an Article Body API (/api/article/body?pathname=...), which returns Markdown that is already rendered: Liquid is resolved, [AUTOTITLE] links get their titles, and redirects are followed. Adding .md to a page URL or sending Accept: text/markdown returns the same Markdown. There is no llms-full.txt. Rendering the raw content/ Markdown from github/docs yourself would be a lot of work: you would need to resolve {% data %} variables and reusables, {% ifversion %} checks backed by 278 feature-flag files, custom tags (octicon, tool, prompt, codetabs) and [AUTOTITLE] links. Use the API instead. The Markdown from the API has three problems: it keeps some raw HTML, its links are relative (/en/...), and it leaves out the plan-availability notice that comes from frontmatter (for example, "Protected branches are available in public repositories with GitHub Free"). That notice matters for a solo learner on a free account. GitHub Docs text is licensed CC-BY-4.0 (the assets, content and data folders) and the site code is MIT. Attribution can be a link that names GitHub Docs, links to the page and the license, and says if you changed the text. The API only serves the current version, so record the fetch date and a content hash, and store the github/docs HEAD commit SHA only as a reference. The Claude Code docs (code.claude.com) have llms.txt, an llms-full.txt of about 9.5 MB, and a .md version of each page. robots.txt sends Content-Signal ai-input=yes, but I found no license for the doc text, and anthropics/claude-code says "All rights reserved". Use links with short summaries rather than storing the full text. The other three sources are openly licensed and safe to ingest with attribution: anthropics/claude-code-action (MIT, including its docs/ and examples/), github/github-mcp-server (MIT), and the MCP docs, where documentation is CC-BY-4.0 and code and specification are Apache-2.0 (older contributions stay MIT while the license changes over). Read-only note: I saved one temporary file (the GitHub Docs page list) in the session scratchpad and changed no project files.

### Findings

- **docs.github.com/llms.txt exists (HTTP 200, text/markdown) and tells LLM tools to use the Page List, Article, Article Body, Search and Versions APIs. /llms-full.txt returns 404.** [high, load-bearing]
  llms.txt says the /api/article/body endpoint returns Markdown that is ideal for LLM use. It also lists the GitHub MCP server and says that server does not currently include docs search. The llms.txt content is curated in github/docs under data/llms-txt.
  Source: <https://docs.github.com/llms.txt>
- **GET /api/article/body?pathname=<path> returns HTTP 200 text/markdown with the page fully rendered and redirects followed. The example old about-pull-requests path 301-redirects to /en/pull-requests/reference/pull-requests, and the API returns that page's content (H1 '# Pull requests').** [high, load-bearing]
  /api/article (JSON with {meta, body}) includes meta.redirectedFrom when it resolves a redirect, so you can detect paths that are not canonical. The body endpoint is plain text and has no redirectedFrom field. Response header: cache-control: public, max-age=60. No rate limits are documented. Docs: https://github.com/github/docs/blob/main/src/article-api/README.md
  Source: <https://docs.github.com/api/article/body?pathname=/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests>
- **Adding .md to a docs.github.com page URL, or requesting it with Accept: text/markdown, returns the same Markdown as the Article Body API.** [medium]
  I observed this behavior (200 text/markdown, same content) but llms.txt does not document it. Use the documented /api/article/body endpoint in the sync job.
  Source: <https://docs.github.com/en/pull-requests/reference/status-checks.md>
- **The Markdown from the API leaves out the plan-availability notice that the frontmatter 'product' field adds. The HTML page shows it. The body also contains raw HTML (for example an <a> with an inline SVG), and its internal links are relative (/en/...).** [high, load-bearing]
  For about-protected-branches, the text 'Protected branches are available in public repositories with GitHub Free...' appears in the HTML page but not in the API body. The source is data/reusables/gated-features/*.md in github/docs. Sanitize the HTML before rendering, and prefix links with https://docs.github.com in citations.
  Source: <https://docs.github.com/api/article?pathname=/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches>
- **Rendering github/docs content/ Markdown outside their site is hard. Files use {% data variables.* %} and {% data reusables.* %}, {% ifversion %} (fpt/ghec/ghes plus feature names from 278 files under data/features), custom Liquid tags, [AUTOTITLE] links, versions frontmatter and redirect_from lists.** [high]
  The custom tag modules are codetabs, data, ifversion, indented-data-reference, octicon, prompt and tool. Example raw file: https://raw.githubusercontent.com/github/docs/main/content/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches.md
  Source: <https://github.com/github/docs/tree/main/src/content-render/liquid>
- **The Page List API (/api/pagelist/en/free-pro-team@latest) returns canonical permalinks only (3,195 paths today). The Versions API lists free-pro-team@latest, enterprise-cloud@latest and enterprise-server@3.18 to 3.22.** [high]
  Use the page list as the allowlist for the sync job, and check stored paths against it to catch renamed or removed pages.
  Source: <https://docs.github.com/api/pagelist/versions>
- **github/docs has two licenses. The README says documentation and content in the assets, content and data folders are Creative Commons Attribution 4.0, and code is MIT (LICENSE-CODE, 'Copyright 2026 GitHub'). The GitHub API reports the repo license as cc-by-4.0.** [high, load-bearing]
  LICENSE: https://github.com/github/docs/blob/main/LICENSE ; LICENSE-CODE: https://github.com/github/docs/blob/main/LICENSE-CODE. CC-BY-4.0 does not grant trademark rights, so do not use GitHub logos as your branding.
  Source: <https://github.com/github/docs/blob/main/README.md>
- **CC-BY-4.0 Section 3(a)(1) requires, when you share the material (including modified versions): keep the creator credit, copyright notice, license notice, disclaimer notice and a link to the material; say if you modified it; and say it is under CC BY 4.0 with the license text or a link. Section 3(a)(2) says you can meet these in any reasonable way, including with a link.** [high, load-bearing]
  Practical form for each lesson and tutor citation: 'Adapted from GitHub Docs, <page title> (<page URL>), © GitHub, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Modified: summarized/excerpted.'
  Source: <https://github.com/github/docs/blob/main/LICENSE>
- **Pin GitHub Docs content by fetch date, not by commit. The Article API serves only the live site (its only optional parameter is apiVersion, for REST pages). github/docs main changes many times a day (HEAD e52ecac841f2b560e27ac4e5da93c6eb2a85b3b3 at 2026-10-14T08:57:53Z).** [medium, load-bearing]
  Store per chunk: canonical path, fetched_at, sha256 of the body, and the github/docs HEAD SHA as a reference only. To find the last commit for a page, query commits?path=content/<path>.md. For example, workflow-syntax.md was last changed at c67a9362 on 2026-10-01. Raw files at a SHA are only useful if you write your own Liquid renderer.
  Source: <https://api.github.com/repos/github/docs/commits/main>
- **In 2026 the pull-request docs were reorganized into get-started/concepts/how-tos/reference sections. The canonical paths for branches, PRs, reviews, merges and status checks are now under /en/pull-requests/... and old /collaborating-with-pull-requests/... URLs redirect.** [high, load-bearing]
  Branches: /en/pull-requests/reference/branches, /en/pull-requests/how-tos/commit-changes/managing-branches-within-your-repository, /en/get-started/using-github/github-flow. PRs: /en/pull-requests/get-started/about-pull-requests, /en/pull-requests/reference/pull-requests, /en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request, .../changing-the-stage-of-a-pull-request. Code review: /en/pull-requests/reference/pull-request-reviews, /en/pull-requests/concepts/giving-reviews, /en/pull-requests/concepts/helping-others-review-your-changes, /en/pull-requests/how-tos/create-pull-requests/requesting-a-pull-request-review, /en/pull-requests/how-tos/review-pull-requests/reviewing-proposed-changes-in-a-pull-request. Required reviews: /en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews. Merges: /en/pull-requests/reference/pull-request-merges, /en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github, /en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request. Merge queue: .../configuring-pull-request-merges/managing-a-merge-queue, /en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request-with-a-merge-queue. Status checks: /en/pull-requests/reference/status-checks, /en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks.
  Source: <https://docs.github.com/api/pagelist/en/free-pro-team@latest>
- **Paths for branch protection, rulesets and CODEOWNERS are under /en/repositories/....** [high, load-bearing]
  /en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches; .../managing-protected-branches/managing-a-branch-protection-rule; .../managing-rulesets/about-rulesets; .../managing-rulesets/creating-rulesets-for-a-repository; .../managing-rulesets/available-rules-for-rulesets; .../managing-rulesets/converting-branch-protections-to-rulesets; CODEOWNERS: /en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners (the file goes in .github/, the root, or docs/, searched in that order; it must be on the PR base branch and under 3 MB).
  Source: <https://docs.github.com/api/pagelist/en/free-pro-team@latest>
- **Paths for GitHub Actions topics: workflow syntax, events, secrets, permissions, GITHUB_TOKEN and environments.** [high, load-bearing]
  /en/actions/get-started/quickstart; /en/actions/get-started/understand-github-actions; /en/actions/get-started/continuous-integration; /en/actions/tutorials/build-and-test-code/python; /en/actions/reference/workflows-and-actions/workflow-syntax (#permissions, #jobsjob_idpermissions); /en/actions/reference/workflows-and-actions/events-that-trigger-workflows (#schedule, #pull_request, #pull_request_target); /en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow; /en/actions/concepts/security/secrets; /en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets; /en/actions/reference/security/secrets; /en/actions/concepts/security/github_token; /en/actions/tutorials/authenticate-with-github_token; /en/actions/reference/security/secure-use; /en/actions/reference/security/securely-using-pull_request_target; /en/actions/concepts/workflows-and-actions/deployment-environments; /en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments; /en/actions/reference/workflows-and-actions/deployments-and-environments; /en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency.
  Source: <https://docs.github.com/api/pagelist/en/free-pro-team@latest>
- **Plan limits: protected branches, rulesets and CODEOWNERS are available on GitHub Free only in public repos; private repos need Pro, Team or Enterprise Cloud. Merge queues need an organization-owned public repo, or Enterprise Cloud for private repos. Environments in private repos need Pro, Team or Enterprise; on Free, Pro and Team, wait timers and required reviewers work only in public repos.** [high, load-bearing]
  Files: protected-branches.md, repo-rules.md, code-owners.md, merge-queue.md, environments.md. On the Free plan, push rulesets are not available for private repos (they need Team). A solo learner on Free should do the hands-on work in a public repo, and the merge queue lesson should be conceptual only.
  Source: <https://github.com/github/docs/tree/main/data/reusables/gated-features>
- **PR authors cannot approve their own pull requests. A solo learner therefore cannot satisfy 'require 1 approval' alone.** [high, load-bearing]
  Design the hands-on task around this: use a second account or a friend, set required approvals to 0 but require status checks, or let repo admins bypass and discuss the tradeoff.
  Source: <https://docs.github.com/api/article/body?pathname=/en/pull-requests/reference/pull-request-reviews>
- **Limits of the schedule trigger: it can be delayed at busy times (the start of each hour), runs only on the default branch, is disabled automatically in public repos after 60 days with no repository activity, cannot run more often than every 5 minutes, and accepts an optional IANA timezone.** [high, load-bearing]
  This affects the project's own scheduled docs re-sync. Schedule it off the hour, and watch for the 60-day auto-disable if the repo is public.
  Source: <https://docs.github.com/api/article/body?pathname=/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>
- **The Claude Code docs offer https://code.claude.com/docs/llms.txt, llms-full.txt (about 9.5 MB) and a .md version of every page (for example /docs/en/github-actions.md, /docs/en/mcp.md). robots.txt sends 'Content-Signal: ai-train=yes, search=yes, ai-input=yes'.** [high]
  robots: https://code.claude.com/robots.txt. Pages I checked return 200: overview, github-actions, code-review, mcp, mcp-quickstart, worktrees, memory, permissions, security, settings, hooks-guide, common-workflows (has a 'Create pull requests' section), best-practices, legal-and-compliance.
  Source: <https://code.claude.com/docs/llms.txt>
- **I found no license that allows reusing the Claude Code docs text. anthropics/claude-code LICENSE.md says '© Anthropic PBC. All rights reserved', with use under the Commercial Terms, and the GitHub API reports no license. I found no public repo for the docs source. The legal-and-compliance page covers use of the product, not reuse of the docs.** [medium, load-bearing]
  ai-input=yes in robots.txt signals that AI retrieval is accepted, but it is not a copyright license to republish. Recommendation: lessons should link and give short original summaries. For tutor RAG, store at most short excerpts with deep links, or keep only the URL and title metadata and fetch live. Legal page: https://code.claude.com/docs/en/legal-and-compliance.md
  Source: <https://github.com/anthropics/claude-code/blob/main/LICENSE.md>
- **anthropics/claude-code-action is MIT-licensed ('Copyright (c) 2025 Anthropic, PBC'), so its docs/ folder (setup, security, configuration, usage, solutions, faq, ...) and examples/*.yml can be ingested with the MIT notice. It releases very often: the latest is v1.0.249 (2026-10-14), and v1 is a moving major tag.** [high, load-bearing]
  Related MIT repos: anthropics/claude-code-security-review, anthropics/claude-code-base-action. The comments in examples/claude.yml still mention an old model id (claude-opus-4-1-20250805), so treat examples as possibly out of date.
  Source: <https://github.com/anthropics/claude-code-action/blob/main/LICENSE>
- **Setup for Claude Code GitHub Actions: /install-github-app (github.com only, needs gh CLI and repo admin), or manual setup with the Claude GitHub App. The App's Contents, Issues and Pull requests permissions are read/write. The secret is ANTHROPIC_API_KEY (input anthropic_api_key) or CLAUDE_CODE_OAUTH_TOKEN (input claude_code_oauth_token, made with `claude setup-token`). Workload identity federation needs `id-token: write`.** [high, load-bearing]
  Only users with write access can trigger the action. allowed_non_write_users and allowed_bots: '*' are flagged as risky, and prompt injection is a documented risk: https://github.com/anthropics/claude-code-action/blob/main/docs/security.md
  Source: <https://code.claude.com/docs/en/github-actions.md>
- **The MCP docs source is github.com/modelcontextprotocol/modelcontextprotocol (docs/ folder, Mintlify docs.json). The LICENSE says the project is moving from MIT to Apache-2.0: new code and specification contributions are Apache-2.0, documentation (excluding specifications) is CC-BY-4.0, and MIT contributions without consent to relicense stay MIT. The GitHub API reports NOASSERTION.** [high, load-bearing]
  modelcontextprotocol.io offers llms.txt, llms-full.txt and .md pages. Docs are versioned by spec date (the latest is /docs/2026-07-28/...), and unversioned paths redirect there. robots.txt sends ai-input=yes. Attribute as CC-BY-4.0 docs; mixed licenses at the file level are possible.
  Source: <https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/LICENSE>
- **github/github-mcp-server is MIT-licensed ('Copyright (c) 2025 GitHub'); the latest release is v2.0.2 (2026-10-08). docs/installation-guides/install-claude.md covers Claude Code with a remote server (https://api.githubcopilot.com/mcp, PAT bearer, `claude mcp add-json`) or locally in Docker with OAuth login.** [high, load-bearing]
  Other docs worth ingesting: docs/remote-server.md, scope-filtering.md, toolsets-and-icons.md, policies-and-governance.md. The guide says scope 'local' is the default and 'project' writes .mcp.json, which matches the --scope rules in code.claude.com/docs/en/mcp.md.
  Source: <https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-claude.md>
- **GitHub Docs now has a page on the Anthropic Claude coding agent in Copilot (public preview; it uses the Claude Agent SDK) and pages on using GHAS with AI coding agents. These are useful CC-BY sources for the 'Claude Code era' framing.** [high]
  Also /en/copilot/concepts/agents/about-third-party-coding-agents and /en/code-security/how-tos/use-ghas-with-ai-coding-agents/scan-for-secrets-with-github-mcp-server. Preview features change quickly, so re-sync often.
  Source: <https://docs.github.com/api/article/body?pathname=/en/copilot/concepts/agents/anthropic-claude>

### Exact snippets (copied from the sources named)

**GitHub Docs LLM APIs (verbatim from llms.txt)** — <https://docs.github.com/llms.txt>

```text
* [Page List API](https://docs.github.com/api/pagelist/en/free-pro-team@latest): Returns every docs page path for a given language and version.
* [Article Body API](https://docs.github.com/api/article/body): Returns the full rendered content of any docs page as markdown. Example: `curl "https://docs.github.com/api/article/body?pathname=/en/get-started/start-your-journey/what-is-github"`
```

**Scheduled workflow with timezone (GitHub Docs, CC BY 4.0)** — <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule>

```yaml
on:
  schedule:
    - cron: '30 5 * * 1-5'
      timezone: "America/New_York"
```

**claude-code-action examples/claude.yml (MIT), first part** — <https://github.com/anthropics/claude-code-action/blob/main/examples/claude.yml>

```yaml
name: Claude Code

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [opened, assigned]
  pull_request_review:
    types: [submitted]

jobs:
  claude:
    if: |
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'pull_request_review' && contains(github.event.review.body, '@claude')) ||
      (github.event_name == 'issues' && (contains(github.event.issue.body, '@claude') || contains(github.event.issue.title, '@claude')))
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
      id-token: write
      actions: read # Required for Claude to read CI results on PRs
    steps:
      - name: Checkout repository
        uses: actions/checkout@v6
        with:
          fetch-depth: 1

      - name: Run Claude Code
        id: claude
        uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Add the remote GitHub MCP server to Claude Code (github-mcp-server, MIT)** — <https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-claude.md>

```bash
claude mcp add-json github '{"type":"http","url":"https://api.githubcopilot.com/mcp","headers":{"Authorization":"Bearer YOUR_GITHUB_PAT"}}'
```

**Add the local GitHub MCP server (Docker, OAuth) to Claude Code (github-mcp-server, MIT)** — <https://github.com/github/github-mcp-server/blob/main/docs/installation-guides/install-claude.md>

```bash
claude mcp add github -e GITHUB_OAUTH_CALLBACK_PORT=8085 -- docker run -i --rm -p 127.0.0.1:8085:8085 -e GITHUB_OAUTH_CALLBACK_PORT ghcr.io/github/github-mcp-server
```

**Claude Code docs robots.txt content signal (exact line)** — <https://code.claude.com/robots.txt>

```text
Content-Signal: ai-train=yes, search=yes, ai-input=yes
```

**PROPOSED (not from docs): per-chunk attribution and provenance record for GitHub Docs** — <https://github.com/github/docs/blob/main/LICENSE>

```json
{
  "source": "GitHub Docs",
  "title": "About protected branches",
  "url": "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches",
  "license": "CC-BY-4.0",
  "license_url": "https://creativecommons.org/licenses/by/4.0/",
  "copyright": "© GitHub",
  "modified": true,
  "fetched_at": "2026-10-14T00:00:00Z",
  "body_sha256": "<hash>",
  "upstream_ref": "github/docs@e52ecac841f2b560e27ac4e5da93c6eb2a85b3b3"
}
```

### Recommendations
- Get GitHub Docs through /api/article/body (or /api/article for JSON with meta.title, breadcrumbs and redirectedFrom). Use /api/pagelist/en/free-pro-team@latest as the canonical allowlist. Do not render raw github/docs Markdown with Liquid yourself.
- Clean each body after fetching: remove or sanitize raw HTML (<a>, <svg>), rewrite relative /en/... links to absolute https://docs.github.com/en/..., and add the plan-availability line back by hand. The API leaves it out, and it matters on a Free account.
- Pin by fetch date plus a hash of the content, and record the github/docs HEAD SHA for reference. In the scheduled re-sync, flag pages whose hash changed or that now redirect, so you can re-check lesson text and quizzes.
- Show a CC BY 4.0 attribution line on every lesson and tutor citation that uses GitHub Docs or MCP docs (title, URL, © owner, license link, 'adapted/summarized'). Have the tutor prompt cite URLs, not just chunk IDs.
- For the Claude Code docs, link and write short original summaries. Do not bulk-ingest llms-full.txt. If the tutor needs Claude Code facts, index only titles, descriptions and URLs from llms.txt, or fetch the .md page live and quote briefly. Ingest the MIT-licensed claude-code-action docs/ and examples/ and the github-mcp-server docs instead.
- Lesson 1, Git and GitHub flow: branches, commits, remotes. Sources: /en/get-started/using-github/github-flow, /en/pull-requests/reference/branches, /en/pull-requests/how-tos/commit-changes/managing-branches-within-your-repository, /en/get-started/git-basics/about-remote-repositories. Task: create a feature branch, commit and push.
- Lesson 2, Pull requests: anatomy, drafts, opening one. Sources: /en/pull-requests/get-started/about-pull-requests, /en/pull-requests/reference/pull-requests, .../create-pull-requests/creating-a-pull-request, .../changing-the-stage-of-a-pull-request. Task: open a draft PR with gh and mark it ready.
- Lesson 3, Code review: giving and getting reviews. Sources: /en/pull-requests/reference/pull-request-reviews, /en/pull-requests/concepts/giving-reviews, /en/pull-requests/concepts/helping-others-review-your-changes, .../review-pull-requests/reviewing-proposed-changes-in-a-pull-request, .../incorporating-feedback-in-your-pull-request. Task: leave suggested changes and resolve them.
- Lesson 4, Merging: merge, squash and rebase, conflicts, reverts. Sources: .../configuring-pull-request-merges/about-merge-methods-on-github, /en/pull-requests/reference/pull-request-merges, .../merge-and-close-pull-requests/resolving-a-merge-conflict-using-the-command-line, .../reverting-a-pull-request. Task: create and resolve a conflict.
- Lesson 5, GitHub Actions basics: workflows, jobs, steps, push and pull_request events. Sources: /en/actions/get-started/understand-github-actions, /en/actions/get-started/quickstart, /en/actions/reference/workflows-and-actions/workflow-syntax, .../events-that-trigger-workflows#pull_request, /en/actions/tutorials/build-and-test-code/python. Task: a CI workflow that runs pytest and ruff on the PR.
- Lesson 6, Status checks and required checks. Sources: /en/pull-requests/reference/status-checks, .../troubleshooting-required-status-checks, /en/pull-requests/how-tos/merge-and-close-pull-requests/automatically-merging-a-pull-request. Task: make CI required, then watch a failing PR get blocked.
- Lesson 7, Branch protection, rulesets, required reviews and CODEOWNERS. Sources: about-protected-branches, managing-a-branch-protection-rule, about-rulesets, creating-rulesets-for-a-repository, available-rules-for-rulesets, about-code-owners, approving-a-pull-request-with-required-reviews. Task in a public repo: a ruleset on main plus a CODEOWNERS file. Discuss the self-approval limit.
- Lesson 8, Secrets, GITHUB_TOKEN, permissions and environments. Sources: /en/actions/concepts/security/secrets, .../use-secrets, /en/actions/concepts/security/github_token, /en/actions/tutorials/authenticate-with-github_token, workflow-syntax#permissions, deployment-environments, manage-environments, /en/actions/reference/security/secure-use, securely-using-pull_request_target. Task: least-privilege permissions plus an environment secret.
- Lesson 9, Scheduled automation, concurrency and merge queue (merge queue as a concept only). Sources: events-that-trigger-workflows#schedule, trigger-a-workflow, control-workflow-concurrency, managing-a-merge-queue, merging-a-pull-request-with-a-merge-queue. Task: a cron docs re-sync that opens a PR with any changes.
- Lesson 10, Claude Code in your local git flow: CLAUDE.md, worktrees, permissions, Claude creating PRs. Link and summarize code.claude.com/docs/en/memory, /worktrees, /common-workflows (Create pull requests), /permissions, /best-practices. Task: Claude Code makes a branch and a PR, and you review it under the ruleset.
- Lesson 11, Claude in GitHub: claude-code-action (@claude), automated review, and the security model. Sources: link and summarize code.claude.com/docs/en/github-actions and /code-review; ingest the MIT claude-code-action README, docs/setup.md, docs/security.md and examples/*.yml. Optional: GitHub Docs /en/copilot/concepts/agents/anthropic-claude. Task: add claude.yml with minimal permissions and pin the action to a SHA.
- Lesson 12, MCP and the GitHub MCP server: what MCP is, scopes and .mcp.json, tokens, security. Sources: modelcontextprotocol.io docs (CC BY 4.0: intro, architecture, security best practices, local server security), code.claude.com/docs/en/mcp and /mcp-quickstart (link only), github-mcp-server install-claude.md and remote-server.md (MIT). Capstone: an agent-assisted PR from issue to merge under protection rules.
- Point hands-on tasks at a public practice repo (or tell learners they need GitHub Pro). Protected branches, rulesets, CODEOWNERS and environment reviewers are gated by plan on private Free repos.

### Risks
- The Article API, the .md suffix and Accept: text/markdown behavior have no published SLA or rate limits. GitHub could change them. Keep a fallback that fetches the HTML page and converts it to Markdown.
- GitHub reorganized its docs in 2026 (the pull-requests section now uses get-started/concepts/how-tos/reference). Hard-coded lesson paths will keep drifting. Redirects hide this, so check against the page list and redirectedFrom.
- The Markdown from the API leaves out plan-gating notices. Lessons or tutor answers built only from it could tell a Free-plan learner that branch protection or CODEOWNERS works on a private repo when it does not.
- API bodies contain raw HTML. If you render them without sanitizing you risk XSS, and the HTML can also inject noise into prompts. Strip it before chunking and embedding.
- There is no clear license to reuse the Claude Code docs text. Storing llms-full.txt in Neon and serving long excerpts could go beyond what Anthropic allows; the ai-input=yes signal is not a copyright grant.
- CC-BY attribution applies to LLM tutor output too, when it closely paraphrases or quotes GitHub or MCP docs. Leaving out citations or license links would break the license.
- claude-code-action ships almost every day and the floating v1 tag moves. Example files contain stale model IDs. Lesson snippets can rot quickly, and following them blindly with broad permissions plus allowed_non_write_users or allowed_bots: '*' creates prompt-injection risk.
- Scheduled workflows in a public repo turn off after 60 days with no activity and can be delayed at the top of the hour. The docs re-sync could stop without anyone noticing.
- The MCP repo's licensing is mixed (some legacy MIT, Apache-2.0, CC-BY-4.0 docs), and its docs are versioned by spec date. Citations should include the versioned URL, which will change when the spec moves on.
- A solo learner cannot approve their own PR, so a lesson that tells them to require 1 approval will leave them stuck.

### Open questions
- Will learners practice in public repos, or should the site assume GitHub Free with private repos and adjust branch-protection, CODEOWNERS and environment lessons to fit?
- Does Anthropic allow using Claude Code docs text for RAG with short quoted excerpts? I found no explicit license. Only the robots.txt Content-Signal ai-input=yes exists, which is not a copyright grant. Low confidence; you could ask Anthropic or limit it to links and metadata.
- Does docs.github.com rate-limit /api/article/body for bulk sync? Nothing is documented; test about 150 pages per run with backoff.
- Should the tutor answer only for GitHub.com (free-pro-team@latest), or also cover the enterprise-cloud variants of the same pages?
- For MCP docs, should you pin to one spec version (currently 2026-07-28) or follow the latest, given that unversioned URLs redirect?
- Should the claude-code-action lesson use the Claude GitHub App with ANTHROPIC_API_KEY (which costs API money), or demonstrate it only with screenshots, so learners avoid usage costs?

### Fact-check (second agent re-read the sources)

Checked live on 2026-10-14 with curl against docs.github.com, raw.githubusercontent.com, api.github.com, git ls-remote, code.claude.com and modelcontextprotocol.io. Results:
- 17 claims confirmed, 1 corrected.
- The corrected claim is the self-approval rule: the fact is right, but the source should be approving-a-pull-request-with-required-reviews, not reference/pull-request-reviews.
- Nuances, not errors:
  - The raw-HTML example is not in the about-protected-branches body, but it does appear in other pages' bodies.
  - llms.txt also lists a Languages API.
  - id-token: write is also needed for the default GitHub App auth.
  - Schedule jobs can be dropped under high load, not only delayed.
- All 45 listed docs paths exist in the live pagelist.
- Process note: my first command saved a copy of llms.txt to the session scratchpad. It made no other writes.

Corrections:
- [corrected] PR authors cannot approve their own pull requests, so a solo learner cannot meet 'require 1 approval' alone. → The fact is correct, but the cited reference page (/en/pull-requests/reference/pull-request-reviews) does not say it. The sentence 'Pull request authors cannot approve their own pull requests' is in the TIP block of approving-a-pull-request-with-required-reviews. That same block notes that repository owners and admins can merge without an approving review unless bypass is restricted, which supports the admin-bypass option. (<https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews>)

Snippet checks:
- Snippet 1 (llms.txt Page List / Article Body lines): none. Both lines match llms.txt verbatim.
- Snippet 2 (schedule with timezone): none. It matches the docs example verbatim; timezone is a sibling key of cron in the same list item.
- Snippet 3 (claude-code-action examples/claude.yml): none. It matches lines 1-36 of the current file verbatim, including actions/checkout@v6, anthropics/claude-code-action@v1 and actions: read.
- Snippet 4 (remote GitHub MCP add-json): none. It matches the guide verbatim. The guide notes it needs Claude Code 2.1.1+; on 2.1.0 and earlier, or if Windows returns 'Invalid input', use the 'claude mcp add --transport http github https://api.githubcopilot.com/mcp -H "Authorization: Bearer ..."' form.
- Snippet 5 (local Docker OAuth): none. It matches the guide verbatim.
- Snippet 6 (code.claude.com robots.txt Content-Signal): none. It matches the live robots.txt exactly.
- Snippet 7 (PROPOSED provenance record): no official schema, so nothing to check field names against. Optional additions: CC BY 4.0 §3(a)(1)(A)(iv) asks you to keep a disclaimer-of-warranties notice (license_url arguably covers it under §3(a)(2)), and a 'modifications' description field such as 'summarized/excerpted' would match §3(a)(1)(B). 'copyright: © GitHub' is fine; the only explicit notice in the repo is 'Copyright 2026 GitHub' in LICENSE-CODE, which covers code.

## Content-source map and lesson inventory for a private learning site: FastAPI, Pydantic AI, and "GitHub for the Claude Code era" (GitHub Docs, Claude Code docs, MCP docs)

**Summary.** I mapped all five sources with read-only `gh api` tree listings and curl, plus Firecrawl and Octen. Tavily refused every call (map, extract, search and crawl) with HTTP 432, a plan usage limit, so it produced no data.

FastAPI has 156 English Markdown files under docs/en/docs, and 152 of them are in the mkdocs nav: tutorial 51, advanced 35, reference 24, how-to 12, deployment 9, plus root pages. The site serves no llms.txt and no .md pages, so content has to come from the GitHub source, with the `{* ../../docs_src/... *}` code includes resolved by our own code.

The Pydantic AI docs moved: ai.pydantic.dev now redirects to https://pydantic.dev/docs/ai/. The source is still the pydantic/pydantic-ai repo's docs/ folder (337 .md files; docs/navigation.yml maps each file to its URL). Its llms.txt is 63,937 bytes (328 links) and llms-full.txt is about 7.0 MB. Every page is also served as `<slug>/index.md`, with an injected preamble that our sync job has to strip.

GitHub Docs has an official Markdown API (pagelist, article/body, article/meta, search) and an llms.txt. Its content is CC-BY-4.0.

The Claude Code docs have a 61,893-byte llms.txt listing 222 English pages, and each page is served as .md. Unlike the others, they carry no open content license ("All rights reserved"; use is subject to Anthropic's Terms of Service).

The MCP docs live in modelcontextprotocol/modelcontextprotocol and are versioned; the latest stable version is 2026-07-28. Docs are CC-BY-4.0 and code/specs are moving from MIT to Apache-2.0.

Pydantic AI is now V2 (v2.56.0, released 2026-10-13; V2 was announced 2026-06-23), so lessons must target the V2 API (capabilities, `conversation=`). The best first FastAPI slice is Request Body, Dependencies and Testing: all three are short, code-heavy, and their hands-on tasks can be graded automatically with pytest.

One deviation from read-only: a curl call wrote 18 Claude Code .md copies to (session temp dir) (temp folder, outside the project). They are listed under risks so you can delete them.

**Engines used:** Firecrawl (firecrawl_scrape: GitHub Article Body API, FastAPI tutorial links, Pydantic AI v2 article, Claude Code worktrees page; firecrawl_search: Pydantic docs domain, FastAPI/Zensical; firecrawl_developer_search: claude-code-action security); Octen (extract: code.claude.com/docs/llms.txt and modelcontextprotocol.io/llms.txt; search: Anthropic/Claude Code docs terms, GitHub Docs API, Pydantic docs hub); Tavily (attempted map, extract, search, crawl: all failed with HTTP 432 plan usage limit, no data); gh api, read-only (FastAPI, pydantic-ai, github/docs, modelcontextprotocol, claude-code-action trees, contents, licenses, releases); curl via Bash (llms.txt files, .md endpoints, docs.github.com Article/Pagelist APIs, redirects, word counts)

### Findings

- **FastAPI English docs: 156 .md files under docs/en/docs (152 listed in mkdocs nav). By folder: tutorial 51, advanced 35, reference 24, how-to 12, deployment 9, root 22 (includes release-notes.md at 711 KB and the non-nav _llm-test.md).** [high] _(via gh api (Bash))_
  Source: tree listing of master (not truncated) and nav parsed from docs/en/mkdocs.yml. Tutorial order in the nav: first-steps, path-params, query-params, body, ..., dependencies/*, security/*, middleware, cors, sql-databases, bigger-applications, stream-json-lines, server-sent-events, background-tasks, metadata, frontend, static-files, testing, debugging. Latest release 0.143.0 (2026-10-08). License MIT.
  Source: <https://github.com/fastapi/fastapi/tree/master/docs/en/docs>
- **FastAPI code-include syntax is `{* ../../docs_src/<dir>/<file>.py [ln[a:b]] [hl[x:y,z]] *}`. Admonitions are `/// note ... ///` and headings carry explicit anchors like `# Request Body { #request-body }`.** [high] _(via gh api (Bash))_
  Examples: body.md uses `{* ../../docs_src/body/tutorial001_py310.py hl[5:9] *}`; sql-databases.md uses `{* ../../docs_src/sql_databases/tutorial001_an_py310.py ln[1:11] hl[7:11] *}`. docs_src holds 464 .py files in 78 folders. Variant suffixes are `_py310` (252 files) and `_an_py310` (83 files, Annotated style); no py39 variants remain. The sync job must resolve these includes, or the RAG chunks lose all code.
  Source: <https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/body.md>
- **fastapi.tiangolo.com serves no llms.txt and no .md versions of its pages. /llms.txt, /llms-full.txt, /tutorial/body.md and /tutorial/body/index.md all return 404. The site is built with Zensical.** [high] _(via Firecrawl scrape + curl (Bash))_
  curl got 404 on all four URLs; https://fastapi.tiangolo.com/tutorial/body/ returns 200 HTML. Firecrawl page metadata shows generator `zensical-0.0.65` (the successor to Material for MkDocs). Firecrawl's links format did not capture the sidebar nav, so the GitHub mkdocs.yml is the reliable inventory.
  Source: <https://fastapi.tiangolo.com/tutorial/>
- **FastAPI ships an official AI-agent skill inside the package (fastapi/.agents/skills/fastapi/SKILL.md plus references/*.md). Users install it with `uvx library-skills`, and it supports Claude Code (.claude/skills).** [high] _(via gh api (Bash))_
  Reference files: dependencies.md, path-operations.md, pydantic.md, responses.md, streaming.md, other-tools.md. It is a compact, current best-practice source for quiz distractors and for the tutor's FastAPI rules. Documented in tutorial/index.md under 'AI Agent Skills'.
  Source: <https://github.com/fastapi/fastapi/blob/master/docs/en/docs/tutorial/index.md>
- **FastAPI candidate-page sizes (words / number of docs_src includes): first-steps 1784/7, path-params 1237/10, query-params 660/6, body 1004/6, response-model 2374/16, handling-errors 1304/8, dependencies/index 1411/4, dependencies-with-yield 1767/11, sql-databases 2310/19, bigger-applications 2847/13, testing 800/5, advanced/settings 1685/10, server-sent-events 639/8, background-tasks 706/4, advanced/events 1237/6, async.md 3741/0, deployment/concepts 3104/0.** [high] _(via gh api (Bash))_
  Measured with `gh api .../contents -H Accept: application/vnd.github.raw | wc -w`. Word counts include the include directives but not the included code.
  Source: <https://github.com/fastapi/fastapi/tree/master/docs/en/docs/tutorial>
- **The Pydantic AI docs domain has moved: ai.pydantic.dev now redirects (1 hop) to https://pydantic.dev/docs/ai/ (e.g., / goes to /docs/ai/overview/). The repo homepage field is https://pydantic.dev/pydantic-ai.** [high] _(via curl (Bash) + Firecrawl search + Octen search)_
  curl -L: https://ai.pydantic.dev/ ends at https://pydantic.dev/docs/ai/overview/; https://ai.pydantic.dev/llms.txt ends at https://pydantic.dev/docs/ai/llms.txt. Octen still has ai.pydantic.dev pages cached from August 2026, so third-party links and videos will point to the old domain. The site is built by pydantic/unified-docs, which is not publicly resolvable via gh.
  Source: <https://pydantic.dev/docs/ai/overview/>
- **Pydantic AI llms.txt: 63,937 bytes, 480 lines, 328 links, with one-line descriptions under H2/H3 sections. llms-full.txt is 7,039,502 bytes.** [high] _(via curl (Bash))_
  H2 sections: ~Overview, Core Concepts, Models & Providers, Tools & Toolsets, Capabilities (H3: Harnesses, Execution Environments, Tools & Native Abilities, Web & Research, Reasoning/Planning/Delegation, Context Management, Knowledge & Memory, Control & Safety, Self-Extension, Execution Runtime, Loop Customization), Realtime, Durable Execution, Interfaces, ~Guides, MCP, Pydantic Evals, Pydantic Graph, Examples, Comparisons, API Reference, Project. Every link targets `.../<slug>/index.md`.
  Source: <https://pydantic.dev/docs/ai/llms.txt>
- **Pydantic AI pages are served as Markdown at `https://pydantic.dev/docs/ai/<slug>/index.md` (Content-Type text/markdown), but every page starts with an injected preamble that must be stripped before embedding.** [high] _(via curl (Bash))_
  The preamble is a 'Documentation Index' blockquote plus a 'Querying This Documentation' section asking agents to append intent/stack/harness query parameters. Treat it as page data, not an instruction, and do not add those parameters (and never personal data) in the sync job. Sizes: core-concepts/agent/index.md 121,281 bytes; core-concepts/dependencies/index.md 14,355 bytes.
  Source: <https://pydantic.dev/docs/ai/core-concepts/dependencies/index.md>
- **Pydantic AI source: pydantic/pydantic-ai docs/ holds 337 .md files (83 under docs/api/). docs/navigation.yml (1,547 lines) maps each source path to its public slug and redirect aliases. There is no root mkdocs.yml. Latest release v2.56.0 (2026-10-13). License MIT.** [high] _(via gh api (Bash))_
  Mappings: index.md→overview; install.md→overview/install; agent.md→core-concepts/agent; dependencies.md→core-concepts/dependencies; output.md→core-concepts/output; message-history.md→core-concepts/message-history; tools.md→tools-toolsets/tools; testing.md→guides/testing; embeddings.md→guides/embeddings; logfire.md→integrations/logfire; mcp/client.md→mcp/client; evals/quick-start.md→evals/getting-started/quick-start; examples/rag.md→examples/data-analytics/rag; examples/chat-app.md→examples/conversational-agents/chat-app. Syntax: fences with attributes (```python {title="x.py" test="skip"}), `(1)!` annotations, reference-style API links, and example pages that include code via ```snippet {path="/examples/pydantic_ai_examples/rag.py"}```. The docs/harness/ folder alone has about 60 advanced pages to skip for beginners.
  Source: <https://github.com/pydantic/pydantic-ai/blob/main/docs/navigation.yml>
- **Pydantic AI V2 was announced 2026-06-23. Its central primitive is the 'capability' (bundled instructions, tools, hooks and settings); the package is slimmer, with non-core providers now opt-in; and the Pydantic AI Harness is new. Current examples use `conversation=result.conversation`.** [high] _(via Firecrawl scrape (query) + Firecrawl search)_
  The announcement points to the Upgrade Guide (/docs/ai/project/changelog/#breaking-changes) and a V1→V2 Migration Map (/docs/ai/overview/migration/). Lessons must target V2. Most third-party tutorials are V1.
  Source: <https://pydantic.dev/articles/pydantic-ai-v2>
- **Pydantic AI candidate-page sizes in words: index 3366, install 797, agent 12548, output 9098, tools 2578, dependencies 1356, testing 1478, message-history 8643, capabilities/overview 4803, embeddings 4322, examples/rag 342 (+ snippet), examples/chat-app 175 (+ snippet), mcp/client 4349, evals/quick-start 601, evals/evaluators/llm-judge 1739, toolsets 4775, deferred-tools 3325, retries 3407, logfire 5255, models/overview 4923.** [high] _(via gh api (Bash))_
  agent.md, output.md and message-history.md must be split into sub-lessons by H2. testing.md covers TestModel and FunctionModel, which make keyless, free hands-on tasks possible. llm-judge.md (sections: When to Use, Configuration, Output Modes, Best Practices, Limitations) fits the rubric-graded 'think deeper' feature.
  Source: <https://github.com/pydantic/pydantic-ai/tree/main/docs>
- **docs.github.com serves Markdown through official APIs. `/api/article/body?pathname=...` returns text/markdown with Liquid already rendered. `/api/article/meta` returns JSON (title, intro, product, breadcrumbs, documentType). `/api/article` returns JSON {meta, body}. Appending `.md` to a normal article URL also returns text/markdown.** [high] _(via Firecrawl scrape + curl (Bash) + Octen search)_
  The requested URL /api/article/body?pathname=/en/actions/writing-workflows/quickstart returned 200 text/markdown, 10,742 bytes, identical to the new canonical path /en/actions/get-started/quickstart (old paths are resolved server-side). Firecrawl's scrape matched. Cache-Control: public, max-age=60. Cleanup needed: inline <svg> octicons, `> \[!NOTE]` alerts, relative links (/en/...) and image paths (/assets/...). The API is documented at /en/get-started/using-github-docs/github-docs-api.
  Source: <https://docs.github.com/api/article/body?pathname=/en/actions/writing-workflows/quickstart>
- **GitHub Docs llms.txt (28,642 bytes, 188 lines) is a curated index, not an exhaustive one. Its 'How to use' section points to the Page List, Article, Article Body, Search, Versions and Languages APIs. The Page List API returns 3,195 English free-pro-team paths (231,713 bytes, newline-separated).** [high] _(via curl (Bash) + Octen search)_
  llms.txt H2 sections: How to use; Building with GitHub for coding agents; Copilot; Get started; Authentication; Account and profile; Pages; Actions; Repositories; Apps; Organizations; Pull requests; REST API; More pages. For a full inventory use https://docs.github.com/api/pagelist/en/free-pro-team@latest. Search example: /api/search/v1?query=actions&client_name=...&version=free-pro-team&language=en.
  Source: <https://docs.github.com/llms.txt>
- **The GitHub Pull requests section has 78 pages, reorganized into get-started / concepts / how-tos / reference / tutorials, and now includes stacked PRs. Actions has 249 pages.** [high] _(via curl (Bash))_
  Key PR pages: get-started/{about-pull-requests (435 words), pull-request-quickstart (1158), reviewing-pull-requests-quickstart (410), about-stacked-prs}; concepts/{helping-others-review-your-changes (625), giving-reviews (334), resolving-reviews}; reference/{branches (898), pull-request-reviews (411), status-checks (1028), pull-request-merges (1082), merge-conflicts}; how-tos/merge-and-close-pull-requests/{automatically-merging-a-pull-request (570), resolving-a-merge-conflict-using-the-command-line (713), troubleshooting-required-status-checks, merging-a-pull-request-with-a-merge-queue}; how-tos/create-pull-requests/changing-the-stage-of-a-pull-request (510, draft PRs).
  Source: <https://docs.github.com/api/pagelist/en/free-pro-team@latest>
- **Branch protection, rulesets and CODEOWNERS pages, with word counts: about-protected-branches 2989, managing-a-branch-protection-rule, about-rulesets 1107, creating-rulesets-for-a-repository 2728, available-rules-for-rulesets 3532, converting-branch-protections-to-rulesets, troubleshooting-rules, about-code-owners 1883, about-merge-methods-on-github, managing-auto-merge-for-pull-requests-in-your-repository, managing-a-merge-queue.** [high] _(via curl (Bash))_
  Path prefixes: /en/repositories/configuring-branches-and-merges-in-your-repository/{managing-protected-branches,managing-rulesets,configuring-pull-request-merges}/... and /en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners. Repo-level review settings: /en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/managing-pull-request-reviews-in-your-repository.
  Source: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets>
- **GitHub Actions basics pages, with word counts: get-started/quickstart 1374, get-started/understand-github-actions 1079, reference/workflows-and-actions/workflow-syntax 23017, reference/workflows-and-actions/events-that-trigger-workflows 10820, concepts/security/secrets 578, how-tos/write-workflows/choose-what-workflows-do/use-secrets 3177, concepts/security/github_token 508, tutorials/authenticate-with-github_token 548, concepts/workflows-and-actions/deployment-environments 160, how-tos/deploy/configure-and-manage-deployments/manage-environments 1775, tutorials/build-and-test-code/python 2272, reference/security/secure-use 4777.** [high] _(via curl (Bash))_
  workflow-syntax must be sliced by H2. The relevant sections are `on`, `on.push...`, `on.<pull_request|pull_request_target>...`, `on.schedule`, `on.workflow_dispatch`, `permissions`, `concurrency`, `jobs.<job_id>.permissions`, `jobs.<job_id>.environment`, `jobs.<job_id>.steps[*]...`. Relevant events: push, pull_request, pull_request_review, pull_request_target, issue_comment, schedule, workflow_dispatch.
  Source: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax>
- **The github/docs repository is dual-licensed: CC-BY-4.0 for documentation content (content/, data/, assets/) and MIT for code. Source files at content/<path>.md use Liquid (`{% data variables.product.prodname_actions %}`, `[AUTOTITLE](...)`), so the rendered API output is the better ingestion source.** [high] _(via gh api (Bash))_
  Example source paths: content/actions/get-started/quickstart.md (8,209 bytes), content/actions/concepts/security/github_token.md, content/pull-requests/reference/status-checks.md, content/repositories/.../about-code-owners.md, content/actions/reference/workflows-and-actions/workflow-syntax.md (79,465 bytes raw).
  Source: <https://github.com/github/docs/blob/main/README.md>
- **Claude Code docs llms.txt: 61,893 bytes, 566 lines, 222 unique English pages, grouped by nested headings (Getting started, Build with Claude Code, Plugins, Administration, Configuration, Reference, Agent SDK, What's New, Resources). It also links 11 language indexes at /docs/_llms/<lang>.txt.** [high] _(via curl (Bash) + Octen extract)_
  GitHub-flow pages: github-actions.md, github-actions-cloud-providers.md, code-review.md, ultrareview.md, worktrees.md, hooks-guide.md, hooks.md, mcp.md, mcp-quickstart.md, memory.md (CLAUDE.md/AGENTS.md), sub-agents.md, agents.md, best-practices.md, common-workflows.md, routines.md, claude-code-on-the-web.md, settings.md, permissions.md, skills.md. Octen extract returned the same llms.txt content.
  Source: <https://code.claude.com/docs/llms.txt>
- **Every Claude Code page is served as Markdown at https://code.claude.com/docs/en/<slug>.md (200, text/markdown), with a 3-line 'Documentation Index' blockquote preamble. The site is built on Mintlify.** [high] _(via curl (Bash) + Firecrawl scrape (links/metadata))_
  Word counts: github-actions 3980, code-review 4982, worktrees 5788, hooks-guide 8408, hooks (reference) 37080, memory 7202, mcp 17082, sub-agents 15056, best-practices 5404, common-workflows 2495, settings 7328, permissions 11758, quickstart 1740, skills 14686, ultrareview 2875, routines 5380, claude-code-on-the-web 5845. Headings in github-actions.md: Setup (/install-github-app quick setup, manual, GitHub App permissions), Interactive and automation modes, Who can trigger runs, Best practices (CLAUDE.md, protect credentials, manage costs), Troubleshooting, Advanced configuration. code-review.md covers REVIEW.md customization and local diff review.
  Source: <https://code.claude.com/docs/en/github-actions.md>
- **The Claude Code docs carry no open content license. The site footer reads '© Anthropic PBC. All rights reserved. Use is subject to applicable Anthropic Terms of Service'. The Legal and compliance page covers product use, not documentation reuse.** [medium] _(via Octen search + curl (Bash))_
  Octen search returned the footer text from the legal-and-compliance page. The page lists Commercial/Consumer Terms, rules for embedding Claude Code in products, and OAuth/credential restrictions. It grants no right to republish the docs. For an owner-only Release 1 RAG index, use short chunks plus links. A later multi-user or paid release needs permission or a link-and-excerpt-only approach. Third-party mirrors (e.g., pjbrito/claude-code-docs on GitHub) exist and should not be ingested.
  Source: <https://code.claude.com/docs/en/legal-and-compliance>
- **anthropics/claude-code-action is MIT-licensed, with reusable docs/*.md (setup, usage, configuration, security, solutions, custom-automations, faq, migration-guide) and examples/*.yml (claude.yml, pr-review-comprehensive.yml, pr-review-filtered-paths.yml, ci-failure-auto-fix.yml, issue-triage.yml, ...).** [high] _(via gh api (Bash) + Firecrawl developer_search)_
  Latest tagged release: v1 (2025-08-26). The repo was pushed 2026-10-14. It is a license-clean source of verbatim workflow examples for the Claude Code + GitHub Actions lessons. Firecrawl developer search surfaced security discussions, e.g., issue #625 on generated workflows missing id-token:write.
  Source: <https://github.com/anthropics/claude-code-action>
- **MCP docs source repo is modelcontextprotocol/modelcontextprotocol. GitHub reports the license as NOASSERTION; the LICENSE file says the project is moving from MIT to Apache-2.0, new code and spec contributions are Apache-2.0, and documentation (excluding specifications) is CC-BY-4.0.** [high] _(via gh api (Bash) + curl + Octen extract)_
  The docs are versioned: docs/docs/{2024-11-05,2025-03-26,2025-06-18,2025-11-25,2026-07-28,draft}/... with specs under docs/specification/<version>. The repo has 359 .md/.mdx files under docs/. Unversioned .md URLs redirect to the latest stable version, e.g., /docs/learn/architecture.md → /docs/2026-07-28/learn/architecture.md (3816 words). llms.txt is 50,288 bytes (a flat list of 362 links under one H1); llms-full.txt is 2,483,137 bytes.
  Source: <https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/LICENSE>
- **Tavily was unavailable for this task. tavily_map, tavily_extract, tavily_search and tavily_crawl all returned HTTP 432 'This request exceeds your plan's set usage limit'.** [high] _(via Tavily (error))_
  All site mapping was done with GitHub tree listings, the docs.github.com pagelist API and llms.txt files instead. These are more complete than a crawler map. No Tavily-sourced claims appear in this report.
  Source: <https://docs.tavily.com/documentation/api-reference/endpoint/map>

### Recommendations
- FASTAPI INVENTORY (12; URL = https://fastapi.tiangolo.com/<path>/; source = github.com/fastapi/fastapi docs/en/docs/<path>.md; pin to tag 0.143.0): 1) First Steps & `fastapi dev`: /tutorial/first-steps/, tutorial/first-steps.md, ~1,780 words. 2) Path Parameters: /tutorial/path-params/, tutorial/path-params.md, ~1,240 words. 3) Query Parameters + validation: /tutorial/query-params/, tutorial/query-params.md (+ query-params-str-validations.md), ~660 words (+16.6 KB). 4) [FIRST SLICE] Request Body with Pydantic models: /tutorial/body/, tutorial/body.md, ~1,000 words, 6 code includes. 5) Response Model: /tutorial/response-model/, tutorial/response-model.md, ~2,370 words. 6) Handling Errors: /tutorial/handling-errors/, tutorial/handling-errors.md, ~1,300 words. 7) [FIRST SLICE] Dependencies: /tutorial/dependencies/, tutorial/dependencies/index.md, ~1,410 words. 8) Dependencies with yield (DB sessions): /tutorial/dependencies/dependencies-with-yield/, tutorial/dependencies/dependencies-with-yield.md, ~1,770 words. 9) SQL Databases (SQLModel): /tutorial/sql-databases/, tutorial/sql-databases.md, ~2,310 words, 19 includes. 10) [FIRST SLICE] Testing with TestClient (+ dependency overrides): /tutorial/testing/, tutorial/testing.md (+ advanced/testing-dependencies.md), ~800 (+370) words. 11) Settings & env vars: /advanced/settings/, advanced/settings.md, ~1,690 words. 12) Streaming with Server-Sent Events (for the tutor chat): /tutorial/server-sent-events/, tutorial/server-sent-events.md, ~640 words. Alternates: bigger-applications (APIRouter, 2,850), background-tasks (710), advanced/events (lifespan, 1,240), async.md (3,740), deployment/concepts (3,100), cors (730).
- Why these 3 for the FastAPI first slice: body, dependencies and testing are each under 1,500 words and code-heavy, and they map directly onto building the site itself. Testing also makes every later hands-on task gradable with pytest/TestClient in GitHub Actions CI. Since the learner has built FastAPI before, first-steps can be a 5-minute warm-up rather than a full lesson.
- PYDANTIC AI INVENTORY (12; URL = https://pydantic.dev/docs/ai/<slug>/; .md at <slug>/index.md; source = github.com/pydantic/pydantic-ai docs/<file>.md; target V2, pin to v2.56.x): 1) Install & first agent: overview/install (+ overview), install.md + index.md, ~800 + 3,370 words. 2) Agents: run, run_sync, streaming, usage limits, conversations: core-concepts/agent, agent.md, 12,550 words, split into 3 sub-lessons by H2. 3) Structured output: core-concepts/output, output.md, ~9,100 words, split. 4) Function tools: tools-toolsets/tools, tools.md, ~2,580 words. 5) Dependencies (typed DI): core-concepts/dependencies, dependencies.md, ~1,360 words. 6) Testing without API keys (TestModel/FunctionModel): guides/testing, testing.md, ~1,480 words. 7) Message history & multi-turn: core-concepts/message-history, message-history.md, ~8,640 words, split. 8) Capabilities (the V2 core primitive): capabilities/overview, capabilities/overview.md, ~4,800 words. 9) Embeddings + RAG: guides/embeddings + examples/data-analytics/rag, embeddings.md + examples/rag.md (+ examples/pydantic_ai_examples/rag.py), ~4,320 + 340 words. 10) Chat app with FastAPI: examples/conversational-agents/chat-app, examples/chat-app.md (+ snippet), ~175 words + code. 11) MCP client: mcp/client, mcp/client.md, ~4,350 words. 12) Evals & LLM Judge (the same pattern the site's rubric grader uses): evals/getting-started/quick-start + evals/evaluators/llm-judge, evals/quick-start.md + evals/evaluators/llm-judge.md, ~600 + 1,740 words. Alternates: retries (3,400), toolsets (4,780), deferred-tools/human-in-the-loop (3,330), integrations/logfire (5,260), models/overview (4,920), overview/migration (V1→V2 map).
- GITHUB FOR THE CLAUDE CODE ERA INVENTORY (12; GitHub URL = https://docs.github.com<path>, Markdown via /api/article/body?pathname=<path>, source github/docs content/<path minus /en>.md; Claude Code URL = https://code.claude.com/docs/en/<slug> with .md): 1) Branches & your first PR: /en/pull-requests/get-started/pull-request-quickstart + /en/pull-requests/reference/branches, ~1,160 + 900 words. 2) Writing a reviewable PR (drafts, descriptions, small diffs): /en/pull-requests/concepts/helping-others-review-your-changes + /en/pull-requests/how-tos/create-pull-requests/changing-the-stage-of-a-pull-request, ~625 + 510 words. 3) Code review on GitHub: /en/pull-requests/get-started/reviewing-pull-requests-quickstart + /en/pull-requests/reference/pull-request-reviews, ~410 + 410 words. 4) Is it ready to merge? (status checks, required reviews, merge methods, conflicts): /en/pull-requests/reference/status-checks + /en/pull-requests/reference/pull-request-merges + /en/pull-requests/how-tos/merge-and-close-pull-requests/resolving-a-merge-conflict-using-the-command-line, ~1,030 + 1,080 + 710 words. 5) Branch protection vs rulesets: /en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches + .../managing-rulesets/about-rulesets (+ available-rules-for-rulesets), ~2,990 + 1,110 (+3,530) words. 6) CODEOWNERS: /en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners, ~1,880 words. 7) First CI workflow for Python: /en/actions/get-started/quickstart + /en/actions/tutorials/build-and-test-code/python, ~1,370 + 2,270 words. 8) Triggers & workflow syntax (push, pull_request, schedule, workflow_dispatch, concurrency): /en/actions/reference/workflows-and-actions/workflow-syntax (H2 slices) + /en/actions/reference/workflows-and-actions/events-that-trigger-workflows (H2 slices), ~1,500 words after slicing. 9) Secrets, GITHUB_TOKEN least-privilege permissions, environments: /en/actions/concepts/security/secrets + /en/actions/concepts/security/github_token + /en/actions/tutorials/authenticate-with-github_token + /en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments, ~580 + 510 + 550 + 1,780 words. 10) Claude Code in a GitHub flow (CLAUDE.md + worktrees): code.claude.com memory.md + worktrees.md, ~7,200 + 5,790 words, sliced. 11) Claude Code GitHub Actions (@claude) + automated Code Review: code.claude.com github-actions.md + code-review.md, plus MIT examples from github.com/anthropics/claude-code-action (examples/claude.yml, pr-review-comprehensive.yml, docs/security.md), ~3,980 + 4,980 words. 12) MCP, hooks and subagents in the loop: modelcontextprotocol.io/docs/2026-07-28/learn/architecture (source docs/docs/2026-07-28/learn/architecture.mdx, ~3,820 words) + code.claude.com mcp.md + hooks-guide.md + sub-agents.md (sliced; 17k / 8.4k / 15k words in full).
- Ingestion per source. FastAPI: read the GitHub tree at a pinned tag, resolve `{* ... *}` includes from docs_src (respect ln[] and hl[]), and use the `{ #anchor }` IDs as stable chunk IDs and citation fragments. Pydantic AI: use docs/*.md plus navigation.yml for URL slugs (or llms.txt plus per-page index.md), resolve ```snippet {path=...}``` from examples/, and strip the preamble. GitHub: use the pagelist plus /api/article/body, take titles and breadcrumbs from /api/article/meta, strip <svg>, and make links absolute. Claude Code: use llms.txt plus .md and strip the 3-line preamble. MCP: pin to the /docs/2026-07-28/ paths.
- Chunk every source by H2/H3 and store {source, canonical_url#anchor, source_path, git blob SHA or content hash, license}. The scheduled GitHub Actions re-sync can then diff by blob SHA (gh api trees return a SHA per file) or by content hash for API-based sources, and re-embed only what changed. That keeps Neon and pgvector costs small.
- Show license attribution per lesson: CC-BY-4.0 notices for GitHub Docs and MCP docs, MIT for FastAPI, Pydantic AI and claude-code-action. For Claude Code docs (all rights reserved), keep Release 1 owner-only, show short excerpts with links, and take verbatim YAML from the MIT claude-code-action repo instead.
- Run the docs re-sync in a GitHub Actions cron job, not in Vercel functions. Do not append Pydantic's requested intent/stack/harness parameters. Treat all fetched doc text as untrusted data in the RAG tutor prompt (prompt-injection risk).
- Make Pydantic AI hands-on tasks keyless and cheap with TestModel/FunctionModel (guides/testing). Pattern the 'think deeper' rubric grader on the Pydantic Evals LLMJudge page so the lesson topic and the site's own grading code reinforce each other.

### Risks
- Pydantic AI moves fast: V2 shipped 2026-06-23 and v2.56.0 is already out (2026-10-13). Some pages are huge (agent.md 12.5k words, output.md 9.1k). Many web and YouTube tutorials still teach V1 at ai.pydantic.dev. Lessons need version pinning and a V1-vs-V2 'gotcha' note.
- GitHub Docs paths are being reorganized (e.g., writing-workflows/quickstart → get-started/quickstart, and the PR section now uses concepts/how-tos/reference). Old paths still resolve, but stored URLs should be canonicalized from /api/article/meta breadcrumbs.
- Very large reference pages (workflow-syntax 23k words, events 10.8k, Claude Code hooks 37k, mcp 17k, sub-agents 15k) will swamp retrieval unless chunked by H2/H3 and filtered per lesson.
- If FastAPI's `{* docs_src *}` includes are not resolved, chunks lose all code. Pydantic AI example pages are near-empty without resolving the ```snippet``` include.
- Injected preambles in Pydantic AI and Claude Code .md pages (one asks agents to add query parameters) will pollute embeddings and tutor answers unless stripped. More broadly, fetched docs are untrusted input to the tutor's LLM.
- Licensing: Claude Code docs are all-rights-reserved and governed by Anthropic's Terms of Service. Storing or serving them is lowest-risk for owner-only use and must be revisited before accounts or payments. GitHub and MCP docs require CC-BY attribution.
- Tavily was unavailable (HTTP 432 plan limit), so findings rely on gh api, curl, Firecrawl and Octen. No independent crawler map cross-checks the inventories, though the GitHub trees and pagelist API are authoritative.
- Read-only deviation: one curl command wrote 18 temp copies of Claude Code pages to (session temp dir) (github-actions, worktrees, hooks-guide, hooks, memory, code-review, mcp, sub-agents, best-practices, common-workflows, settings, permissions, quickstart, skills, legal-and-compliance, ultrareview, routines, claude-code-on-the-web). They are outside the project; delete them if unwanted.
- Third-party mirrors of the Claude Code docs exist on GitHub. Ingesting them would bring in stale content and licensing problems.

### Open questions
- Is storing chunks of the Claude Code docs in a private Neon pgvector index acceptable under Anthropic's Terms for Release 1? And what is the plan for multi-user Release 2: link-out only, or ask Anthropic?
- Which LLM provider and API key will power the tutor and grader? This decides whether Pydantic AI hands-on tasks use real models or only TestModel/FunctionModel.
- Should the FastAPI database lesson follow the docs' SQLModel approach, or teach psycopg/asyncpg + pgvector directly to match the site's own stack?
- Should Track 3 teach rulesets as the primary mechanism (GitHub is steering there) with classic branch protection as background, and should it cover the new stacked PRs and merge queue?
- Which MCP docs version should lessons pin: 2026-07-28 (current stable), or follow the unversioned redirect, which will move to the next version automatically?
- Does the GitHub Docs Search API require the client_name parameter for automated use, and are there rate limits for nightly pagelist + article/body syncs? Neither is stated in the llms.txt text that was fetched.
- Should FastAPI's bundled agent skill (fastapi/.agents/skills/fastapi) be ingested as a tutor source, given it is version-locked to the installed FastAPI?
