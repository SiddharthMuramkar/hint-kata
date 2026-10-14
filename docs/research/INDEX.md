# Research archive — index

Produced on 2026-10-14 during the scoping session, before any code was written.
Three research waves ran in parallel (22 topics), each topic was re-read by a second "fact-check" agent, and a
critic agent looked for contradictions across topics. Search engines used: Firecrawl, Octen, Tavily (hit its plan
limit part-way), plus direct reads of official docs, source repos and package registries.

Each file has a header with: which phase needs it, licence and attribution notes, and what it covers. Facts about
fast-moving tools go stale quickly. Before relying on a number or a config key, open the linked source.

| File | Phase | What it covers |
|---|---|---|
| [claude-code-features.md](claude-code-features.md) | 1 | Subagents, skills, workflows, /goal, /loop, output styles, hooks, settings, permissions, auto mode, MCP, worktrees, plugins, model routing |
| [docs-sources-and-licenses.md](docs-sources-and-licenses.md) | 1, 2 | Where FastAPI, Pydantic AI, GitHub, Claude Code and MCP docs live as Markdown; syntax quirks; pinning; licences; 12-lesson inventories |
| [pydantic-ai-and-openrouter.md](pydantic-ai-and-openrouter.md) | 1 | Pydantic AI v2.56 API facts; OpenRouter integration, slugs, prices, spend caps, privacy, embeddings API |
| [llm-models-embeddings-evals.md](llm-models-embeddings-evals.md) | 1, 2 | Model prices and behaviour, embeddings, Logfire, testing and pydantic-evals, cost estimates |
| [github-plans-and-actions.md](github-plans-and-actions.md) | 1 | Free vs Pro, ruleset JSON, security features, CodeQL, auto-merge, Dependabot, pinned action SHAs, gh commands |
| [frontend-and-local-stack.md](frontend-and-local-stack.md) | 1 | Primer options, FastAPI Jinja2 + SSE + vanilla JS, safe Markdown, type checker, fsrs, SQLite pitfalls, tests |
| [learning-science.md](learning-science.md) | 1 | Evidence behind the lesson loop: retrieval, feedback, spacing, tutor guardrails, LLM grading calibration |
| [hands-on-and-prior-art.md](hands-on-and-prior-art.md) | 1 | GitHub Skills pattern, CLIs, Pyodide status, Codespaces quotas, checker per track |
| [trace-transcripts.md](trace-transcripts.md) | 1, 2 | What a "trace transcript" is, schema, capture pipelines, storage, UX |
| [rag-and-content-pipeline.md](rag-and-content-pipeline.md) | 2 | Chunking, include resolvers, Article API, pgvector/psycopg, hybrid search, re-sync, retrieval evals |
| [neon.md](neon.md) | 2 | Lakebase Postgres plans, pgvector, pooling, Vercel integration, branch actions, auth, MCP |
| [vercel.md](vercel.md) | 2 | Python runtime, limits, Services beta, previews, protection, domains, pricing, AI Gateway |
| [names-and-domains.md](names-and-domains.md) | 2 | Name candidates, collisions, domain prices and DNS notes |
| [cross-topic-critique.md](cross-topic-critique.md) | all | Contradictions and resolutions, open questions, top risks, decision list, platform cross-check |

Raw scraped page text is never stored in this repo. The fetch script (phase 1) writes it to `.cache/docs/`,
which is gitignored.
