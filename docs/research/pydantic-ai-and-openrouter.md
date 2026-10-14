# Pydantic AI v2 and OpenRouter

_Research archive. Checked against primary sources on 2026-10-14. Facts about fast-moving tools (Claude Code, Pydantic AI, FastAPI, GitHub, OpenRouter) go stale quickly: re-check before relying on a number._

- **Needed by:** Phase 1
- **Licence / attribution notes:** Pydantic AI: MIT. OpenRouter docs: cited by link only.
- **Covers:** Pydantic AI 2.56 API facts (agents, output, tools, deps, testing, evals, embeddings, UI adapters, gateway), the docs move, V1→V2 breaks, OpenRouter integration, model slugs and prices, spend caps, privacy, embeddings API

## Pydantic AI as a content source (docs, license, versions) and as a dependency (current V2 API facts), with a 12-lesson track outline

**Summary.** The Pydantic AI docs have moved off ai.pydantic.dev. Old URLs, deep links included, now 301-redirect to pydantic.dev/docs/ai/<slug>/. llms.txt (64 KB, about 328 links) and llms-full.txt (7.0 MB, includes the rendered API reference) are at the new address, and every page has a rendered Markdown copy at <slug>/index.md. The source Markdown is still in github.com/pydantic/pydantic-ai/docs: 337 .md files, about 3.6 MB. There is no mkdocs.yml in the repo any more. docs/navigation.yml maps each source path to its public slug for a private "unified-docs" site, so you can ingest raw files from GitHub and still cite canonical pydantic.dev URLs. The raw sources use a lot of MkDocs-style markup that a renderer or chunker must handle or strip: 346 admonitions, 29 tab blocks, 45 custom ```snippet {path=...}``` includes, 323 mkdocstrings ::: directives, 788 code fences with {title=/test=/lint=...} attributes, 286 code annotations, about 3,560 reference-style API links, and 137 `pip/uv-add` pseudo-commands. The license is MIT (Copyright (c) Pydantic Services Inc. 2024 to present), and the docs sit in the same repo under the same LICENSE. Keep the notice and link back to the source. Pydantic AI is now on V2: v2.0.0 shipped 2026-06-23 and the latest is v2.56.0 (2026-10-13), with roughly 4 minor releases a week and about 100 docs commits in the last 10 days. The docs are not versioned (only current docs are served), so pin the package version and record the git SHA of the docs you ingest. V2 renamed or reshaped a lot of the V1 API that most tutorials and LLM memory still use: the openai: prefix now means the Responses API, builtin_tools is now native_tools, instrument=/history_processors= moved to capabilities, run_stream_events is an async context manager, and Dataset(name=...) is required. Lessons and the tutor must be grounded in the V2 docs. Things that map directly onto your stack: a built-in Embedder class (OpenAI, Google, Cohere, Voyage, Bedrock, local sentence-transformers), VercelAIAdapter/AGUIAdapter.dispatch_request for streaming to a frontend from FastAPI, TestModel/FunctionModel/ALLOW_MODEL_REQUESTS for tests, and pydantic_evals LLMJudge for rubric grading.

### Findings

- **Docs moved to pydantic.dev/docs/ai/. Old ai.pydantic.dev URLs, deep links included, 301-redirect to the new paths (e.g. /agents/ -> /docs/ai/core-concepts/agent/, /testing/ -> /docs/ai/guides/testing/, /ui/vercel-ai/ -> /docs/ai/integrations/ui/vercel-ai/).** [high, load-bearing]
  Checked with curl -sIL: HTTP/2 301, location https://pydantic.dev/docs/ai/core-concepts/agent/. ai.pydantic.dev/llms.txt redirects to https://pydantic.dev/docs/ai/llms.txt.
  Source: <https://ai.pydantic.dev/agents/>
- **llms.txt is at https://pydantic.dev/docs/ai/llms.txt (63,937 bytes, about 328 page links grouped by section). llms-full.txt is at https://pydantic.dev/docs/ai/llms-full.txt (7,039,502 bytes, about 1,192 H1 sections, includes the rendered API reference). A rendered Markdown copy of each page is at <canonical-url>/index.md.** [high, load-bearing]
  Both files and the per-page index.md copies start with an injected preamble ('Documentation Index' / 'Querying This Documentation') that asks AI agents to add intent/stack/harness query parameters to every fetch. A re-sync job should strip this text before chunking and should not send those parameters by default. The rendered pages are lossy: admonition titles become plain paragraphs, annotation markers become '# (1)' plus trailing paragraphs, and tables flatten into one cell per line. Links become absolute pydantic.dev URLs, which is useful for citations.
  Source: <https://pydantic.dev/docs/ai/llms.txt>
- **The source Markdown is in pydantic/pydantic-ai on branch main under docs/: 337 .md files totalling about 3,663 KB.** [high]
  Files / size by folder: root 44 / 1,009 KB (core concepts: agent.md 110 KB, message-history.md 75 KB, output.md 71 KB, tools-advanced.md 76 KB); harness 67 / 934 KB; models 27 / 432 KB; evals 21 / 304 KB; capabilities 26 / 285 KB; realtime 17 / 196 KB; durable_execution 8 / 161 KB; ui 3 / 84 KB; examples 21 / 61 KB; comparisons 12 / 45 KB; mcp 3 / 46 KB; graph 5 / 69 KB; api 83 / 37 KB (mkdocstrings stubs only). The tree response was not truncated.
  Source: <https://api.github.com/repos/pydantic/pydantic-ai/git/trees/main?recursive=1>
- **The repo has no mkdocs.yml. docs/navigation.yml (53.7 KB, schema https://pydantic.dev/docs/schemas/repository-navigation.schema.json) is the canonical sidebar for 'pydantic/unified-docs'. It maps each source path to a public slug and lists redirect aliases.** [high, load-bearing]
  Example entry: path 'agent.md' -> slug 'core-concepts/agent' -> https://pydantic.dev/docs/ai/core-concepts/agent/. pydantic/unified-docs returns 404 via the API (private), so the site build config is not public. Use navigation.yml to turn raw-file chunks into canonical citation URLs.
  Source: <https://github.com/pydantic/pydantic-ai/blob/main/docs/navigation.yml>
- **MkDocs-specific syntax counts across all 337 source files: 346 '!!! type "title"' admonitions, 4 '???' collapsibles, 29 '=== "Tab"' tabs (some with '{#id}'), 45 custom ```snippet {path="/examples/..." fragment="..."}``` includes, 0 pymdown '--8<--' includes, 323 '::: module.path' mkdocstrings directives (with YAML 'options: members:'), 788 code fences with attributes, 286 '# (n)!' code annotations, about 3,560 reference-style links '[Text][pydantic_ai.module.Name]', 137 'pip/uv-add' and 27 'python/uv-run' pseudo-commands, 3 '{{ video(...) }}' macros, 35 '{:target="_blank"}' attr_lists, 94 '{#anchor}' heading IDs, 12 mermaid blocks, '#!python' inline highlighting, and YAML frontmatter (title/description/status) in 234 files.** [high, load-bearing]
  Fence attribute keys by frequency: title 594, test 213, lint 65, names 51, path 45, requires 42, hl_lines 20, fragment 17, typecheck 14, noqa 11, line_length 7, max_py 6, dunder_name 5, call_name 5, format 3, py 2. Code examples show printed output as '#> ...' comment lines. Snippet includes point at repo-root /examples/pydantic_ai_examples/*.py, and 'fragment' selects named regions. docs/AGENTS.md documents the conventions (reference links, admonitions not GitHub alerts, fence attributes such as {test="skip" lint="skip"}). Reference links like [X][pydantic_ai.agent.Agent] have no target in raw Markdown, so they need a resolver that maps them to /docs/ai/api/... or they must be stripped to plain text.
  Source: <https://github.com/pydantic/pydantic-ai/tree/main/docs>
- **License: MIT, 'Copyright (c) Pydantic Services Inc. 2024 to present'. The grant covers 'the Software and associated documentation files', and the copyright and permission notice must be included in all copies or substantial portions.** [high, load-bearing]
  The GitHub API reports spdx MIT and PyPI reports MIT. No separate docs license was found. The docs live in the same repo, so the MIT LICENSE most plausibly covers them (medium confidence on the docs specifically; no explicit statement). Attribution practice: show the MIT notice on a credits or licence page, link each cited chunk to its pydantic.dev URL, and do not imply endorsement. The pydantic/skills repo is also MIT.
  Source: <https://github.com/pydantic/pydantic-ai/blob/main/LICENSE>
- **Latest release is v2.56.0, published 2026-10-13T23:35:15Z. PyPI pydantic-ai, pydantic-ai-slim and pydantic-evals are all at 2.56.0, with requires_python >=3.11.** [high, load-bearing]
  From gh api repos/pydantic/pydantic-ai/releases/latest and https://pypi.org/pypi/pydantic-ai/json.
  Source: <https://github.com/pydantic/pydantic-ai/releases/tag/v2.56.0>
- **Release cadence: V1 shipped 2025-09-05, the V2 betas ran 2026-05-21 to 2026-06-10, and stable v2.0.0 shipped 2026-06-23. There have been 66 v2.x.y releases since then (about 4 a week). A V1 maintenance line (v1.107.0 to v1.107.7) continues. About 100 commits touched docs/ between 2026-10-04 and 2026-10-14.** [high, load-bearing]
  Version policy: no intentional breaking changes in minor releases. Deprecated features are removed only in the next major, which will not come sooner than 3 months after V2.0. V1 gets security fixes for at least 6 months after V2 stable (so until at least about 2026-12-23). Beta modules can change without notice. Adding new message parts or stream events is not counted as a breaking change.
  Source: <https://github.com/pydantic/pydantic-ai/releases>
- **The docs are not versioned publicly: only the current docs are served, and /docs/ai/v1/, /docs/ai/latest/, /docs/ai/1.x/ and ai.pydantic.dev/1.0/ all return 404.** [medium, load-bearing]
  The site JS contains a generic 'version-selector' component, but I found no Pydantic AI version URLs. I could not confirm whether the live site builds from main or from the latest release tag. Since docs change daily, the live site may describe unreleased features.
  Source: <https://pydantic.dev/docs/ai/project/version-policy/>
- **V2 broke many V1 APIs that tutorials and LLM training data still use. The upgrade guide and a 'V1 → V2 Migration Map' page list them.** [high, load-bearing]
  Key changes for a beginner track: (1) 'openai:' now uses the Responses API; use 'openai-chat:' for Chat Completions. (2) Model names without a provider prefix (Agent('gpt-5')) raise UserError. (3) builtin_tools -> native_tools; UrlContextTool -> WebFetchTool. (4) mcp_servers= -> toolsets=; per-transport MCP classes -> MCPToolset. (5) Agent(instrument=), event_stream_handler=, prepare_tools= and history_processors= moved to capabilities. (6) Agent.run_stream_events() is an async context manager only. (7) result.usage(), result.timestamp() and stream.get() became properties; stream_responses() -> stream_response(). (8) Agent.to_ag_ui()/AGUIApp -> AGUIAdapter; to_a2a moved upstream. (9) Pydantic Evals takes keyword-only arguments and requires Dataset(name=...). (10) The default end_strategy is now 'graceful'. (11) Default extras are slimmer (bedrock, groq and mistral are no longer included). (12) An unparameterized Agent is typed Agent[object, str]. Migration map: https://pydantic.dev/docs/ai/overview/migration/
  Source: <https://pydantic.dev/docs/ai/project/changelog/>
- **Agent.__init__ on main has 18 parameters: model, output_type, instructions, system_prompt, deps_type, name, description, model_settings, retries, validation_context, tools, toolsets, defer_model_check, end_strategy, metadata, tool_timeout, max_concurrency, capabilities. There are five ways to run an agent: run, run_sync, run_stream (plus run_stream_sync), run_stream_events, and iter.** [high, load-bearing]
  The docs recommend instructions over system_prompt. When message_history is passed, only the current agent's instructions are sent, and @agent.instructions functions are re-evaluated on every run. Instructions come in three forms: static (constructor), dynamic (@agent.instructions, which takes RunContext), and runtime (an instructions= argument to run). Tools are registered with @agent.tool (first parameter ctx: RunContext[DepsT]), @agent.tool_plain, or tools=[fn, Tool(fn, takes_ctx=...)]. Docstrings become tool descriptions. ctx.deps holds the deps= value passed at run time. The final value is result.output. Source: https://pydantic.dev/docs/ai/core-concepts/agent/
  Source: <https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/agent/__init__.py>
- **Structured output: output_type takes Pydantic models, unions and functions. The output modes are ToolOutput (default), NativeOutput, PromptedOutput and TextOutput, plus StructuredDict for a custom JSON schema. @agent.output_validator can raise ModelRetry to make the model try again. run_stream can stream partial structured output.** [high]
  Section anchors in docs/output.md: #structured-output, Output functions, Output modes, #structured-dict, #output-validator-functions, Streamed Results (stream_text, structured streaming, cancelling streams).
  Source: <https://pydantic.dev/docs/ai/core-concepts/output/>
- **Multi-turn chat: result.all_messages() and new_messages() (plus *_json variants) are passed back as message_history=. ModelMessagesTypeAdapter (de)serializes stored histories. New in V2-era docs: result.conversation, a Conversation object that bundles messages, usage, conversation_id and deferred tool requests, passed back as conversation=. sanitize_messages() must be applied to any history a client submits.** [high, load-bearing]
  The docs say message_history is trusted server-side state. sanitize_messages (pydantic_ai.messages) strips client-supplied system prompts, unsafe file URLs and unresolved tool calls. The UI adapters apply this sanitization automatically. ConversationTypeAdapter serializes a Conversation. V1-serialized histories still deserialize in V2. If you pass message_history without usage, UsageLimits budgets reset every turn.
  Source: <https://pydantic.dev/docs/ai/core-concepts/message-history/>
- **Testing: TestModel (pydantic_ai.models.test) and FunctionModel (pydantic_ai.models.function, with AgentInfo) are swapped in with Agent.override(model=..., deps=..., toolsets=...). Setting pydantic_ai.models.ALLOW_MODEL_REQUESTS = False blocks real model calls, and also blocks embedding calls. capture_run_messages() (top-level pydantic_ai) inspects the exchanged messages. The docs use pytest with anyio.** [high, load-bearing]
  In V2, capture_run_messages also captures partial messages from interrupted runs, marked state='interrupted'. TestModel cannot emulate native tools; use agent.override(model=TestModel(), native_tools=[]). Embeddings have TestEmbeddingModel and Embedder.override.
  Source: <https://pydantic.dev/docs/ai/guides/testing/>
- **Pydantic Evals: from pydantic_evals import Case, Dataset; evaluators come from pydantic_evals.evaluators (EqualsExpected, Contains, IsInstance, LLMJudge, MaxDuration, G-Eval and others). Usage is Dataset(name=..., cases=[Case(name=, inputs=, expected_output=)], evaluators=[...]), then dataset.evaluate_sync(fn) or await dataset.evaluate(fn), then report.print().** [high, load-bearing]
  LLMJudge parameters: rubric, model, include_input, include_expected_output, model_settings, score={'include_reason': True}, assertion=False|{...}. The default output is a pass/fail assertion with a reason. Source sets _default_model = 'openai:gpt-5.2', which set_default_judge_model() can change. pydantic_evals.evaluators.llm_as_a_judge also defines judge_output, judge_input_output, judge_input_output_expected and judge_output_expected, which a runtime grader could call directly. I read the function definitions but did not confirm that all four are exported. A standard-quality-metrics page has RAG faithfulness and relevance rubrics.
  Source: <https://pydantic.dev/docs/ai/evals/getting-started/quick-start/>
- **Embeddings are built in: from pydantic_ai import Embedder. Embedder('openai:text-embedding-3-small') provides await embed_query(text) and await embed_documents(list), and returns result.embeddings. EmbeddingSettings(dimensions=...) is in pydantic_ai.embeddings. Provider prefixes include openai, google, cohere, voyageai, bedrock, sentence-transformers (local), and OpenAI-compatible azure:, ollama: and vllm:.** [high, load-bearing]
  Also available: count_tokens(), TestEmbeddingModel, and OpenAIEmbeddingModel / SentenceTransformerEmbeddingModel classes. Install extras: pydantic-ai-slim[openai], [sentence-transformers], [voyageai]. Pydantic AI does not prescribe a vector DB (it names pgvector as an option) and has no reranker class. The official RAG example uses pgvector with text-embedding-3-small stored in vector(1536) and notes that pgvector HNSW supports up to 2,000 dimensions.
  Source: <https://pydantic.dev/docs/ai/guides/embeddings/>
- **UI streaming adapters: pydantic_ai.ui.UIAdapter has the subclasses VercelAIAdapter (pydantic_ai.ui.vercel_ai) and AGUIAdapter (pydantic_ai.ui.ag_ui). On FastAPI or Starlette you add @app.post('/chat') and return await VercelAIAdapter.dispatch_request(request, agent=agent).** [high, load-bearing]
  For more control: build_run_input(body), from_request(), run_stream_native(), transform_stream(), encode_stream() (SSE strings) and streaming_response(). SSE_CONTENT_TYPE is in pydantic_ai.ui. The Vercel adapter targets AI SDK v5 by default. Pass sdk_version=6 for v6 features such as tool approval with useChat's addToolApprovalResponse. Extras: 'ui' (starlette), 'ag-ui' (ag-ui-protocol + starlette), 'web' (starlette + uvicorn). The default pydantic-ai install includes the Web UI.
  Source: <https://pydantic.dev/docs/ai/integrations/ui/overview/>
- **Logfire instrumentation is logfire.configure() followed by logfire.instrument_pydantic_ai(). Optionally add logfire.instrument_httpx(capture_all=True). Agent.instrument_all() or the Instrumentation capability (capabilities=[Instrumentation(settings=...)]) work with any OTel backend. Use logfire.configure(send_to_logfire=False) to export only to another backend.** [high]
  The default instrumentation format is version 5 in V2, and Agent(instrument=...) was removed. Logfire Personal plan: free, 10M records/month, hard-capped, 1 seat, 30-day retention. Team plan: $49/mo (https://pydantic.dev/pricing).
  Source: <https://pydantic.dev/docs/ai/integrations/logfire/>
- **Pydantic AI Gateway is a multi-provider proxy managed through Logfire. Model strings take the form 'gateway/<api_format>:<model>' (e.g. 'gateway/openai:gpt-5.2', 'gateway/anthropic:claude-sonnet-4-6'), and the key is read from the env var PYDANTIC_AI_GATEWAY_API_KEY. Supported upstreams: OpenAI, Anthropic, Google Cloud, Groq, Bedrock. Requires pydantic-ai >= 1.16.** [high, load-bearing]
  Pricing per https://pydantic.dev/pricing and https://pydantic.dev/ai-gateway: BYOK has no markup on any plan (up to 3 BYOK credentials on Personal and Team, unlimited on Growth and Enterprise). Built-in providers carry a 5% markup on Personal and Team and 3% on Growth and Enterprise Cloud/Dedicated. Built-in providers on Personal require a credit card. Other features: spend caps per project, user or key; failover and load-balancing endpoints. No separate free usage allowance is stated.
  Source: <https://pydantic.dev/docs/ai/overview/gateway/>
- **Model strings have the form '<provider>:<model>', e.g. Agent('anthropic:claude-sonnet-4-6') with ANTHROPIC_API_KEY, or Agent('openai:gpt-5.2') with OPENAI_API_KEY. 'openai:' resolves to OpenAIResponsesModel, and 'openai-chat:' resolves to OpenAIChatModel (Chat Completions).** [high, load-bearing]
  The model IDs in the docs change quickly. Current pages mention claude-sonnet-4-6, claude-opus-4-8, claude-fable-5-1, gpt-5.2, gpt-5.5, gpt-6-sol and gpt-5.6-luna. Keep model IDs in config (env vars) rather than lesson text, and check them against each provider's model list before release. Pydantic AI drops temperature, top_p and top_k automatically for newer Claude Opus models. OpenAI page: https://pydantic.dev/docs/ai/models/openai/
  Source: <https://pydantic.dev/docs/ai/models/anthropic/>
- **Install: 'pip/uv-add pydantic-ai' (Python 3.11+) brings in the OpenAI, Anthropic and Google SDKs plus the CLI, MCP, Evals, Web UI and Logfire integrations. pydantic-ai-slim[...] installs only the extras you name (e.g. openai, anthropic, logfire, evals, ui, ag-ui, sentence-transformers, retries).** [high, load-bearing]
  For a Mac with little RAM, use pydantic-ai-slim[anthropic,openai,logfire,evals,ui] and avoid sentence-transformers. That extra pulls in torch, and even small local models such as embeddinggemma-300m use roughly 1+ GB (the RAM figure is my estimate, not from the docs).
  Source: <https://pydantic.dev/docs/ai/overview/install/>
- **For the 'Claude Code era' track, Pydantic maintains an official Claude Code plugin and skill ('claude plugin install pydantic-ai@claude-plugins-official', or the marketplace pydantic/skills with 'ai@pydantic-skills' and 'logfire@pydantic-skills'). Pydantic AI Harness also ships a PydanticAIDocs capability that fetches docs pages from pydantic/pydantic-ai:main on demand.** [high]
  PydanticAIDocs exposes one tool, read_pyai_docs(topic), with topics capabilities, hooks, tools, tools-advanced, toolsets and agent. Harness is versioned 0.x and may break in minor releases (https://pydantic.dev/docs/ai/harness/pydantic-ai-docs/). The maintainers' own tooling reads raw docs from GitHub main, which supports raw-source ingestion. There is also a GitHub Agentic Workflows page (harness/gh-aw) about running a Pydantic AI agent in GitHub Actions.
  Source: <https://pydantic.dev/docs/ai/overview/coding-agent-skills/>
- **The docs include a FastAPI chat-app example and a pgvector RAG example that closely match this project's architecture.** [high]
  RAG example: docs sections are embedded into pgvector and the agent gets a retrieve tool through deps. The build step uses the OpenAI SDK directly, not Embedder. Chat app: https://pydantic.dev/docs/ai/examples/conversational-agents/chat-app/ (FastAPI, stores chat history). Example code is in /examples/pydantic_ai_examples/ and pulled into the docs through ```snippet``` includes.
  Source: <https://pydantic.dev/docs/ai/examples/data-analytics/rag/>

### Exact snippets (copied from the sources named)

**FastAPI endpoint streaming an agent to a Vercel AI SDK frontend** — <https://pydantic.dev/docs/ai/integrations/ui/overview/>

```python
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from pydantic_ai import Agent
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

agent = Agent('openai:gpt-5.2')

app = FastAPI()

@app.post('/chat')
async def chat(request: Request) -> Response:
    return await VercelAIAdapter.dispatch_request(request, agent=agent)
```

**Multi-turn chat via message_history** — <https://pydantic.dev/docs/ai/core-concepts/message-history/>

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-5.2', instructions='Be a helpful assistant.')

result1 = agent.run_sync('Tell me a joke.')
print(result1.output)
#> Did you hear about the toothpaste scandal? They called it Colgate.

result2 = agent.run_sync('Explain?', message_history=result1.new_messages())
print(result2.output)
#> This is an excellent joke invented by Samuel Colvin, it needs no explanation.
```

**Unit test pattern: block real calls, override model, capture messages (excerpt)** — <https://pydantic.dev/docs/ai/guides/testing/>

```python
pytestmark = pytest.mark.anyio  # (1)!
models.ALLOW_MODEL_REQUESTS = False  # (2)!


async def test_forecast():
    conn = DatabaseConn()
    user_id = 1
    with capture_run_messages() as messages:
        with weather_agent.override(model=TestModel()):  # (3)!
            prompt = 'What will the weather be like in London on 2024-11-28?'
            await run_weather_forecast([(prompt, user_id)], conn)  # (4)!
```

**Built-in Embedder quick start** — <https://pydantic.dev/docs/ai/guides/embeddings/>

```python
from pydantic_ai import Embedder

embedder = Embedder('openai:text-embedding-3-small')


async def main():
    # Embed a search query
    result = await embedder.embed_query('What is machine learning?')
    print(f'Embedding dimensions: {len(result.embeddings[0])}')
    #> Embedding dimensions: 1536

    # Embed multiple documents at once
    docs = [
        'Machine learning is a subset of AI.',
        'Deep learning uses neural networks.',
        'Python is a programming language.',
    ]
    result = await embedder.embed_documents(docs)
    print(f'Embedded {len(result.embeddings)} documents')
    #> Embedded 3 documents
```

**LLMJudge rubric variants (Pydantic Evals)** — <https://pydantic.dev/docs/ai/evals/evaluators/llm-judge/>

```python
LLMJudge(rubric='Response is polite')

# Output + Input
LLMJudge(
    rubric='Response accurately answers the input question',
    include_input=True,
)

# Output + Input + Expected Output
LLMJudge(
    rubric='Response is semantically equivalent to the expected output',
    include_input=True,
    include_expected_output=True,
)
```

**Logfire instrumentation** — <https://pydantic.dev/docs/ai/integrations/logfire/>

```python
import logfire

from pydantic_ai import Agent

logfire.configure()  # (1)!
logfire.instrument_pydantic_ai()  # (2)!

agent = Agent('openai:gpt-5.2', name='hello_world_agent', instructions='Be concise, reply with one sentence.')  # (4)!
result = agent.run_sync('Where does "hello world" come from?')  # (3)!
print(result.output)
```

**Pydantic AI Gateway key and model string** — <https://pydantic.dev/docs/ai/overview/gateway/>

```bash+python
export PYDANTIC_AI_GATEWAY_API_KEY="pylf_v..."

from pydantic_ai import Agent

agent = Agent('gateway/openai:gpt-5.2')
result = agent.run_sync('Where does "hello world" come from?')
print(result.output)
```

**Raw-source MkDocs syntax a renderer must handle (tabs from gateway.md; snippet include from examples/weather-agent.md; mkdocstrings from api/agent.md)** — <https://github.com/pydantic/pydantic-ai/blob/main/docs/gateway.md>

```markdown
=== "uv"

    ```bash
    uv sync -P pydantic-ai
    ```

=== "pip"

    ```bash
    pip install -U pydantic-ai
    ```

```snippet {path="/examples/pydantic_ai_examples/weather_agent.py"}```

::: pydantic_ai.agent
    options:
        members:
            - Agent
```

### Recommendations
- Ingest raw Markdown from GitHub (git/trees + raw.githubusercontent.com at a recorded commit SHA) rather than llms-full.txt. Use docs/navigation.yml to map each file to its canonical citation URL https://pydantic.dev/docs/ai/<slug>/. Store source_path, slug, heading anchor, commit SHA and content hash for each chunk.
- For release 1, limit the RAG corpus to the ~44 root pages plus ui/, evals/, models/{overview,anthropic,openai}.md and examples/{rag,chat-app}.md (roughly 1.5 MB). Skip harness/ (0.x API, 934 KB), realtime/, durable_execution/ and api/ (mkdocstrings stubs with no prose).
- Preprocessor for raw sources: remove YAML frontmatter but keep `description` as metadata. Turn `!!! type "Title"` and `??? type` blocks into labelled blockquotes (de-indent the body). Turn `=== "Tab"` blocks into labelled sub-sections. Expand ```snippet {path=...}``` from /examples, or drop it and link to GitHub. Remove fence attributes, keeping `title` as a caption. Turn `# (n)!` annotations into footnotes. Resolve `[X][pydantic_ai.a.B]` to plain `X` or to an API URL. Expand `pip/uv-add pkg` into `pip install pkg` / `uv add pkg`. Remove `{:...}`, `{#...}`, `#!python` and `{{ video(...) }}`.
- If you use the rendered pydantic.dev .../index.md pages instead, strip the 'Documentation Index' and 'Querying This Documentation' preamble before embedding. The tutor must never see it as an instruction, and the sync job should not append the intent/stack/harness query parameters it requests.
- Pin `pydantic-ai-slim[anthropic,openai,logfire,evals,ui]==2.56.0` and `pydantic-evals==2.56.0` (exact pins, uv.lock), and upgrade on purpose. Add a weekly GitHub Actions re-sync that diffs content hashes and re-embeds only changed chunks. Write lessons against V2 only, and link the V1→V2 Migration Map in lesson 1.
- Use pydantic_ai.Embedder with 'openai:text-embedding-3-small'. Optionally use EmbeddingSettings(dimensions=...) to keep the pgvector column size fixed, and store the model name and dimension alongside the vectors. Do not run sentence-transformers locally on a low-RAM Mac.
- Serve the tutor chat with VercelAIAdapter.dispatch_request in a FastAPI POST route (AI SDK v5 by default; sdk_version=6 only if the frontend uses AI SDK v6). Run sanitize_messages (or let the adapter do it) on any history the client sends.
- Build the grader agent with output_type set to a Pydantic model (score, rubric_hits, feedback). Unit-test the quiz, tutor and grader agents with TestModel/FunctionModel and ALLOW_MODEL_REQUESTS=False in CI. Use pydantic_evals Dataset + LLMJudge offline to calibrate the grader rubrics against hand-scored answers.
- Keep model IDs in environment/config (e.g. TUTOR_MODEL='anthropic:claude-sonnet-4-6'), not in lesson text or code samples. The docs' model IDs change monthly.
- Show the MIT notice ('Copyright (c) Pydantic Services Inc. 2024 to present' plus the permission text) on a credits page, attribute every cited chunk with a link to the canonical pydantic.dev URL, and avoid Pydantic branding that implies endorsement.
- Suggested 12-lesson Pydantic AI track (canonical slugs under https://pydantic.dev/docs/ai/): L1 What is an agent: install, API keys, model strings, run_sync (overview/install, core-concepts/agent, models/overview, models/anthropic, models/openai, overview/migration). L2 Instructions & model settings: static, dynamic and runtime instructions vs system_prompt (core-concepts/agent#instructions). L3 Structured output: output_type, output modes, output_validator, ModelRetry (core-concepts/output). L4 Function tools: @agent.tool, @agent.tool_plain, tools=[...], docstrings as schema (tools-toolsets/tools, then toolsets). L5 Dependencies & RunContext: deps_type, ctx.deps, override (core-concepts/dependencies). L6 Streaming: run_stream/stream_text, run_stream_events, event types (core-concepts/agent#running-agents, core-concepts/output#streamed-results). L7 Multi-turn chat & persistence: message_history, ModelMessagesTypeAdapter, Conversation, sanitize_messages (core-concepts/message-history, core-concepts/persistence). L8 Serving agents from FastAPI to a UI: VercelAIAdapter, AG-UI (integrations/ui/overview, integrations/ui/vercel-ai, examples/conversational-agents/chat-app). L9 RAG with Embedder + pgvector (guides/embeddings, examples/data-analytics/rag). L10 Testing agents: TestModel, FunctionModel, override, ALLOW_MODEL_REQUESTS, capture_run_messages (guides/testing). L11 Evals & LLM-as-judge: Dataset, Case, evaluators, LLMJudge rubrics (evals/evals, evals/getting-started/quick-start, evals/evaluators/llm-judge, evals/evaluators/standard-quality-metrics). L12 Production basics: Logfire tracing, retries, usage limits, Gateway, version policy (integrations/logfire, core-concepts/retries, overview/gateway, project/version-policy). Optional L13: multi-agent and MCP client (guides/multi-agent-applications, mcp/client, capabilities/overview).

### Risks
- Fast API churn: about 4 releases a week and about 100 docs commits in 10 days. Lessons, quizzes and rubrics drift from the live docs within weeks unless they are pinned to a version and re-checked by CI (e.g., run the lesson code samples against the pinned version in GitHub Actions).
- The docs are unversioned and may track main, so the tutor's RAG can cite features that are not in your pinned release. Record the commit SHA per chunk and consider syncing from the release tag (v2.x.y) instead of main.
- LLM knowledge and most third-party tutorials describe V1 (OpenAIModel, builtin_tools, mcp_servers=, Agent(instrument=), result.usage(), to_ag_ui). The tutor agent's own priors can contradict the V2 docs, so its instructions must say to prefer the retrieved context over memory.
- The rendered pydantic.dev Markdown and llms*.txt contain text addressed to AI agents (the query-parameter request). If it is embedded without stripping, it becomes injected instructions in the tutor's context.
- Unresolved MkDocs syntax (reference links, annotations, tabs, snippet includes) produces noisy chunks and broken citations, and the 45 snippet-included examples are empty in raw Markdown unless you resolve them.
- Grading LLM output with an LLM judge (pydantic_evals LLMJudge, or a custom grader agent) is non-deterministic. Use temperature 0, structured output and calibration sets, and show students the rubric.
- The Gateway's built-in providers on the free Personal plan require a credit card and carry a 5% markup. BYOK directly to Anthropic/OpenAI is simpler for release 1.
- Vercel streaming duration limits for a Python FastAPI backend were not verified here. Long tutor responses over SSE may hit function timeouts, so check this in the Vercel research track.

### Open questions
- Does pydantic.dev/docs/ai build from main or from the latest release tag? This is not documented, and the build repo (pydantic/unified-docs) is private.
- Is the documentation content (as opposed to the code) explicitly covered by the MIT LICENSE? The LICENSE text says 'associated documentation files', but the docs have no explicit licence statement. Low risk, but unconfirmed.
- Are judge_output / judge_input_output_expected exported publicly from pydantic_evals.evaluators so a runtime grader can call them directly, or are they semi-internal? I saw only the function definitions in llm_as_a_judge.py.
- Which AI SDK major version will the frontend use (v5 is the adapter default, v6 needs sdk_version=6)? This decides whether tool-approval UI is available.
- Should the tutor answer only from the pinned-version docs, or also cite newer docs while flagging the version mismatch?
- Exact license and terms for pydantic.dev/llms-full.txt: is it the same MIT content? Probably yes, but I found no terms page for the docs site.

### Fact-check (second agent re-read the sources)

I checked every claim against live sources on 2026-10-14: curl on pydantic.dev and ai.pydantic.dev, raw.githubusercontent.com, the GitHub API, PyPI JSON, and a streamed repo tarball to recount the syntax. All 17 claims hold, so none is marked corrected. The 'correction' fields on confirmed claims add precision only.

Points worth carrying forward:
- The llms.txt preamble differs from the per-page index.md preamble: only index.md has the 'Documentation Index' block, and it points at pydantic.dev/llms.txt.
- Agent(builtin_tools=) maps to capabilities=[NativeTool(...)], not to a native_tools= constructor argument.
- The AI Gateway is an add-on on Enterprise plans.
- The default install does not include the 'ui' or 'ag-ui' extras, or fastapi.
- The four judge_* helpers are exported in llm_as_a_judge.__all__.

The syntax counts are a snapshot of main. {:target="_blank"} recounted at 42 rather than 35, and others differ by 1 to 5. The docs change daily (109 commits touched docs/ in the 10-day window).

Downloaded copies of llms.txt, llms-full.txt and agent index.md are in (session scratchpad) (scratch only; no project files were touched).

Snippet checks:
- FastAPI/VercelAIAdapter snippet: none. It matches dispatch_request.py on the UI overview page word for word. fastapi is not part of any pydantic-ai extra, so install it separately.
- Multi-turn message_history snippet: none (matches the message-history page exactly).
- Unit test excerpt: none. It matches the raw docs/testing.md, which uses '# (n)!' markers; the rendered page shows '# (n)'. Imports (pytest, models, capture_run_messages, TestModel, weather_app) are left out of the excerpt.
- Embedder quick start: none (matches embeddings_quickstart.py exactly).
- LLMJudge rubric variants: none (matches the llm-judge page; 'from pydantic_evals.evaluators import LLMJudge' is left out).
- Logfire instrumentation: none (matches the logfire page; the raw source uses '# (n)!' markers).
- Gateway key + model string: none (matches the gateway page; it mixes bash export and Python in one block).
- Raw MkDocs syntax: none. Tabs match docs/gateway.md lines 80-90, the snippet include matches docs/examples/weather-agent.md line 32, and the '::: pydantic_ai.agent' options/members YAML matches docs/api/agent.md. The real members list is much longer than the single '- Agent' shown.

## OpenRouter as the LLM gateway for Pydantic AI v2.56 (OPENROUTER_API_KEY): integration, Claude 5.5 pricing, fees, spend caps, privacy, embeddings, evals, known issues

**Summary.** Pydantic AI v2.56.0 (tagged 2026-10-13, the current PyPI release) supports OpenRouter natively. It ships both `OpenRouterModel` (a subclass of OpenAIChatModel) and `OpenRouterProvider` (base URL https://openrouter.ai/api/v1). You install the `pydantic-ai-slim[openrouter]` extra (it only adds `openai>=3.26.0`), and the provider reads `OPENROUTER_API_KEY`. Model strings look like `openrouter:<lab>/<slug>`, for example `openrouter:anthropic/claude-haiku-5.5`. The provider turns `anthropic/claude-haiku-5.5` into the Anthropic profile `claude-haiku-5-5`, so Claude 5.5 rules apply: thinking by default, no forced tool choice on Sonnet 5.5, and JSON-schema output support. That means a bare structured `output_type` on these thinking Claude models switches to NativeOutput (`response_format` json_schema) on its own. Streaming works, and Anthropic `cache_control` prompt caching passes through, either via the unified `cache=True` setting or via the `openrouter_cache_*` settings and `CachePoint`. OpenRouter's live catalog on 2026-10-14 lists `anthropic/claude-haiku-5.5` at $0.10 in / $0.50 out per 1M tokens (for prompts up to 100K tokens; $0.50/$2.50 above that) and `anthropic/claude-sonnet-5.5` at $2/$10. Both match Anthropic's first-party prices, and the cheapest strong alternatives are `openai/gpt-6-luna` ($0.10/$0.50) and Gemini Flash-Lite variants ($0.10 to $0.30 in). OpenRouter does not mark up inference; it charges 5.5% when you buy credits (8% on Business), and BYOK is fee-free up to $25,000 a month of list-price usage, then 5%. Each API key can have its own USD spend cap (`limit`, with an optional daily, weekly or monthly reset) on every plan, and paid models have no plan-based rate limits. OpenRouter now has an OpenAI-compatible embeddings API (POST /api/v1/embeddings; for example `openai/text-embedding-3-small` at $0.02/1M). Pydantic AI's `Embedder('openrouter:...')` should route to it through OpenAIEmbeddingModel; I verified the code path but did not test it live. pydantic-evals `LLMJudge` accepts an `openrouter:` model string, but its default judge is `openai:gpt-5.2`, so set the default judge explicitly.

### Findings

- **Pydantic AI v2.56.0 has both OpenRouterModel and OpenRouterProvider. OpenRouterModel subclasses OpenAIChatModel (Chat Completions). OpenRouterProvider's base_url is https://openrouter.ai/api/v1.** [high]
  Release v2.56.0 was published 2026-10-13 and PyPI's latest pydantic-ai-slim is 2.56.0 (uploaded 2026-10-13T23:50Z). The provider's `api_key` falls back to the OPENROUTER_API_KEY environment variable and raises UserError if neither is set. Optional OPENROUTER_APP_URL and OPENROUTER_APP_TITLE set the HTTP-Referer and X-Title attribution headers.
  Source: <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pydantic_ai/providers/openrouter.py>
- **The install extra is `pydantic-ai-slim[openrouter]`. Its only dependency is `openai>=3.26.0`, the same openai package as the [openai] extra but without tiktoken.** [high]
  pyproject at the tag has `openrouter = ["openai>=3.26.0"]`. The docs page shows `uv add "pydantic-ai-slim[openrouter]"`. Use the separate `evals` extra or the pydantic-evals package for LLMJudge.
  Source: <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pyproject.toml>
- **Model strings use the form `openrouter:<upstream>/<slug>`, for example `openrouter:anthropic/claude-sonnet-5.5`. A slug without '/' raises UserError. `~provider/model` latest aliases are accepted.** [high]
  infer_model sends model_kind 'openrouter' to OpenRouterModel. KnownModelName has no openrouter: entries, so a typo in a slug is not caught by type checkers and only fails at runtime as an HTTP error. Docs example: `Agent('openrouter:anthropic/claude-sonnet-4.6')`.
  Source: <https://pydantic.dev/docs/ai/models/openrouter/>
- **OpenRouterProvider picks the upstream lab's profile from the slug prefix and replaces '.' with '-' for Anthropic. So `anthropic/claude-haiku-5.5` resolves to `claude-haiku-5-5` and `anthropic/claude-sonnet-5.5` to `claude-sonnet-5-5`, and both inherit the Claude 5.5 capability flags.** [high]
  Those flags are: supports_json_schema_output=True; thinking_enabled_by_default for Haiku 5.5 and Sonnet 5.5; thinking_always_enabled and supports_forced_tool_choice=False for Sonnet 5.5 and Opus 5.5; no sampling params. The gateway layer also sets supports_inline_system_prompts=False and openai_chat_supports_max_completion_tokens=False, and enables cache_control only for anthropic/ and google/ upstreams (Anthropic: up to 4 breakpoints, TTL 5m or 1h). Google upstreams get a legacy JSON-schema transformer that inlines $defs (issue #3617).
  Source: <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pydantic_ai/profiles/anthropic.py>
- **OpenRouterModelSettings exposes OpenRouter's routing and reasoning controls. All of them are `openrouter_`-prefixed and are sent to OpenRouter in extra_body.** [high]
  The fields are openrouter_models (fallback model list), openrouter_provider (order, allow_fallbacks, require_parameters, data_collection 'allow'/'deny', zdr, only, ignore, quantizations, sort 'price'/'throughput'/'latency'/'exacto', max_price), openrouter_preset, openrouter_transforms (['middle-out']), openrouter_reasoning (effort / max_tokens / exclude / enabled), openrouter_usage ({'include': True}), and openrouter_cache_instructions / openrouter_cache_messages / openrouter_cache_tool_definitions (True, '5m' or '1h'). The unified `thinking` setting maps to openrouter_reasoning.effort (True→medium, False→none, xhigh→high). Pydantic AI ignores thinking=False on always-thinking models such as Sonnet 5.5.
  Source: <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pydantic_ai/models/openrouter.py>
- **Structured output on Anthropic models through OpenRouter: tool output is the default mode. When forcing an output tool would stop a thinking Claude model from thinking, Pydantic AI uses NativeOutput (OpenAI-style `response_format: {type: json_schema, json_schema: {...}}`) instead. This happens by default for Haiku 5.5 and Sonnet 5.5, because both think by default.** [high]
  Model._default_structured_output_mode returns 'native' when the default mode is 'tool', the request has output tools, the profile has supports_json_schema_output, and forced tool choice would disable thinking. The OpenRouter docs page says a bare structured output_type uses Native Output while the request thinks. This was fixed after issue #8675: `tool_choice=required` used to be sent to Opus 5.5 and returned a 400. PRs #8808 and #8812 merged 2026-09-28, before v2.56.0. You can still pass NativeOutput(...) explicitly. OpenRouter treats `response_format` as a soft routing preference, so it is sent only to providers that support it.
  Source: <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pydantic_ai/models/__init__.py>
- **OpenRouter's Claude 5.5 behavior: Sonnet 5.5 and Opus 5.5 reject forced tool_choice ('required' or a named tool) with a 400. Haiku 5.5 accepts forced tool choice but skips thinking for that call. All three reject assistant prefill and non-default temperature/top_p/top_k. Reasoning is mandatory on Sonnet 5.5: `effort:'none'` or `enabled:false` returns a 400.** [high]
  Defaults: Haiku 5.5 thinks adaptively at effort `medium` and can be turned off. Sonnet 5.5 thinks at effort `high` and cannot be turned off through Chat Completions. Budgets (`reasoning.max_tokens`) are not forwarded; use effort instead. OpenRouter requests summarized reasoning display. Thinking blocks are account-bound: OpenRouter keeps Haiku 5.5 replays on the producing provider, and Sonnet 5.5 replays within the Anthropic, Claude-on-AWS and Azure group, never Bedrock or Vertex. Haiku 5.5 uses a tokenizer that produces about 30% more tokens than Haiku 4.5. The minimum cacheable prompt is 512 tokens.
  Source: <https://openrouter.ai/docs/cookbook/evaluate-and-optimize/model-migrations/claude-5-5.md>
- **Anthropic prompt caching (cache_control) passes through OpenRouter. Pydantic AI places breakpoints using the unified `cache=True` setting, openrouter_cache_instructions / openrouter_cache_messages / openrouter_cache_tool_definitions, or CachePoint markers.** [high]
  TTL is '5m' (default) or '1h' and is only sent to Anthropic. Earlier 5m breakpoints are raised to 1h when needed, and excess breakpoints beyond 4 are dropped oldest-first. Check result.usage.cache_write_tokens and cache_read_tokens. OpenRouter uses provider sticky routing for 10 minutes after a cached request, and a `session_id` can pin it explicitly. Anthropic pricing on OpenRouter: 5m write 1.25x input, 1h write 2x, read 0.1x (0.05x on Sonnet 5.5).
  Source: <https://openrouter.ai/docs/guides/best-practices/prompt-caching.md>
- **Streaming is supported and is billed the same as non-streaming.** [high]
  OpenRouterModel uses OpenRouterStreamedResponse, a subclass of OpenAIStreamedResponse that also handles error chunks arriving mid-stream. The OpenAI Chat path sends stream_options include_usage=True. OpenRouter's pricing FAQ says pricing is per token whether or not you stream.
  Source: <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pydantic_ai/models/openrouter.py>
- **Exact slugs and prices from OpenRouter's live catalog (fetched 2026-10-14): anthropic/claude-haiku-5.5 costs $0.10 input and $0.50 output per 1M tokens (cache read $0.01, 5m write $0.125, 1h write $0.20). Prompts at or over 100K tokens cost $0.50/$2.50 (read $0.05, write $0.625/$1.00). anthropic/claude-sonnet-5.5 costs $2.00/$10.00 (cache read $0.10, 5m write $2.50, 1h write $4.00). Both have 1M context and 128K max output.** [high]
  These match Anthropic's first-party pricing page (Sonnet 5.5 cache hits are 0.05x input, i.e. $0.10). Some regional endpoints (google-vertex/us and europe, azure/us, bedrock us-east-1) charge about 10% more. `:batch` variants cost 50% less. Latest aliases are ~anthropic/claude-haiku-latest and ~anthropic/claude-sonnet-latest. Haiku 5.5 was created 2026-10-07 and Sonnet 5.5 on 2026-09-28. Neither lists `temperature` in supported_parameters.
  Source: <https://openrouter.ai/api/v1/models>
- **The cheapest serious alternatives with tools and structured_outputs support (OpenRouter catalog, 2026-10-14): openai/gpt-6-luna $0.10/$0.50 ($0.20/$0.75 above 272K tokens; openai/flex endpoint $0.05/$0.25), google/gemini-2.5-flash-lite $0.10/$0.40, google/gemini-3.1-flash-lite $0.25/$1.50, google/gemini-3.5-flash-lite $0.30/$2.50, deepseek/deepseek-v4-flash $0.091/$0.182, qwen/qwen3.8-flash $0.15/$0.47.** [high]
  Pydantic AI v2.56 has profile entries for gpt-6-luna (reasoning on by default, accepts effort 'none'). Prices only; I did not evaluate quality for tutoring or grading.
  Source: <https://openrouter.ai/api/v1/models>
- **OpenRouter does not mark up inference. Its fee is charged when you buy credits: 5.5% on Standard (pay-as-you-go) and 8% on Business, never on individual requests. Failed or fallback attempts are not charged for model tokens.** [high]
  Standard and Business have no minimum spend. Unused credits are refundable only within 24 hours, and platform fees are non-refundable. The FAQ says crypto payments carry a fee, but the percentage did not render in the fetched page. The 1% discount applies only if you opt in to letting OpenRouter use your prompts.
  Source: <https://openrouter.ai/pricing>
- **BYOK fee: Standard and Business include $25,000 of list-price inference per month through your own provider keys at no fee. Usage above that is charged 5% of what the same model and provider would cost on OpenRouter, deducted from credits.** [high]
  Source: <https://openrouter.ai/docs/faq>
- **Per-key spend caps are available on every plan. Set `limit` (USD), `limit_reset` ('daily', 'weekly' or 'monthly'; resets at 00:00 UTC; leave unset for a lifetime cap) and `include_byok_in_limit` in the dashboard key dialog, or with POST /api/v1/keys or PATCH /api/v1/keys/{key_hash} using a management API key.** [high]
  When the cap is reached, requests fail with 403 'Key limit exceeded' (limit_source openrouter_key_limit); the limits page also lists openrouter_key_limit under 402 handling. GET https://openrouter.ai/api/v1/key returns limit, limit_remaining, limit_reset, budgets and effective_budget. Keys can also take `expires_at`. Management API keys require Standard or above according to the pricing table.
  Source: <https://openrouter.ai/docs/guides/best-practices/capping-shared-agent-keys.md>
- **New or low-balance prepaid accounts are subject to an 'in-flight spending budget'. Concurrent paid requests are pre-charged an estimate (input tokens plus max_tokens, or a fixed cap if max_tokens is unset). If the total exceeds a fraction of your balance, requests get a 402 even though the balance is positive.** [high]
  The 402 metadata has reason 'in_flight_budget_exhausted' (transient, comes with Retry-After) or 'weight_exceeds_budget' (lower max_tokens or add credits). Accounts above a balance threshold are exempt. The exact threshold and fraction are not published.
  Source: <https://openrouter.ai/docs/api_reference/limits.md>
- **Paid-model rate limits: OpenRouter sets no plan-based rate limit on paid models. Limits come from the upstream provider, fallback routing retries other providers, and only very large bursts get a 429 from DDoS protection. Free `:free` models are limited to 20 requests/minute and 50 requests/day, or 1,000/day after $10 of credits have been purchased.** [high]
  Failed attempts count toward the free daily cap, and a negative balance blocks free models.
  Source: <https://openrouter.ai/pricing>
- **Account privacy controls: OpenRouter stores only request metadata by default. Prompt and response logging and 'OpenRouter use of inputs/outputs' are both opt-in and off by default. Separate toggles (for paid and for free models) block routing to providers that may train on your data. Account-wide allowed and ignored provider lists exist in Settings > Privacy and combine with each request's provider.only and provider.ignore.** [high]
  Request-level `provider.data_collection: 'deny'` excludes providers that store data. If no provider meets your account privacy settings, the request errors instead of falling back to a less private provider.
  Source: <https://openrouter.ai/docs/guides/routing/provider-selection.md>
- **Zero Data Retention (ZDR) can be enforced per model group in privacy settings (Anthropic, OpenAI, Google, SpaceXAI, all other), per guardrail, or per request with provider.zdr=true. Enforcing the Anthropic group removes first-party Anthropic endpoints and leaves Bedrock and Vertex.** [high]
  OpenRouter's ZDR endpoint list (2026-10-14): Haiku 5.5 on google-vertex (global, us, europe) and amazon-bedrock (default, us-east-1, eu-west-1); Sonnet 5.5 on google-vertex (global, us, europe) and amazon-bedrock; gpt-6-luna on azure (and us, eu); gemini-3.5-flash-lite on google-vertex; openai/text-embedding-3-small on azure. In-memory implicit caching does not count as retention.
  Source: <https://openrouter.ai/docs/guides/features/zdr.md>
- **OpenRouter has an OpenAI-compatible embeddings API: POST https://openrouter.ai/api/v1/embeddings, with models listed at GET /api/v1/embeddings/models. Prices per 1M input tokens (2026-10-14): openai/text-embedding-3-small $0.02, openai/text-embedding-3-large $0.13, qwen/qwen3-embedding-8b $0.01, voyageai/voyage-4-lite $0.02, google/gemini-embedding-001 $0.15, google/gemini-embedding-2 $0.20. Free variants include nvidia/nemotron-3-embed-1b:free.** [high]
  Batch input arrays are supported, and some models accept images. A rerank API also exists. Sticky routing does not apply to embeddings (x-session-id is used only for grouping).
  Source: <https://openrouter.ai/docs/api_reference/embeddings.md>
- **Pydantic AI's Embedder should work with OpenRouter through the `openrouter:` prefix. infer_embedding_model sends every OpenAIChatCompatibleProvider (which includes 'openrouter') to OpenAIEmbeddingModel with that provider, which calls client.embeddings.create against https://openrouter.ai/api/v1.** [medium]
  So `Embedder('openrouter:openai/text-embedding-3-small')` is the expected usage. EmbeddingSettings supports `dimensions` and `extra_body`, so routing preferences can be passed as extra_body={'provider': {...}}. This is code-path only: the embeddings docs do not mention OpenRouter by name, I found no OpenRouter embedding tests, and I did not run it (no key, read-only task).
  Source: <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pydantic_ai/embeddings/__init__.py>
- **pydantic-evals LLMJudge accepts `model: Model | KnownModelName | str`, and the string goes through infer_model, so `LLMJudge(rubric=..., model='openrouter:anthropic/claude-sonnet-5.5')` works. The default judge is `'openai:gpt-5.2'`, which needs OPENAI_API_KEY unless you override it.** [high]
  Use `pydantic_evals.evaluators.llm_as_a_judge.set_default_judge_model(...)` or pass `model=` on each judge. LLMJudge also takes model_settings, so you can pass OpenRouterModelSettings for ZDR or effort.
  Source: <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_evals/pydantic_evals/evaluators/llm_as_a_judge.py>
- **Known open Pydantic AI issues with OpenRouter: CachePoint handling (#7467, #9236), billed cost not copied into RequestUsage.cost (#7150), and a stale provider-name list plus missing routing fields (#8885, #10004).** [high]
  #7467: OpenRouterModel rejects a CachePoint at the start of a later UserPromptPart with UserError. #9236: the SystemReminders capability emits a leading CachePoint that OpenRouter rejects. #7150: OpenRouter's billed cost stays in provider_details (upstream_inference_cost etc.) and is not copied into RequestUsage.cost. #8885: KnownOpenRouterProviders lists 11 providers OpenRouter no longer serves. #10004: preferred_min_throughput and max latency fields are missing from OpenRouterProviderConfig. Closed and fixed before 2.56: #8675 (forced tool_choice to Opus 5.5) and #8887 (quantization and exacto sort values).
  Source: <https://github.com/pydantic/pydantic-ai/issues/9236>
- **The OpenRouter code path does not apply the Anthropic `anthropic_disallows_sampling_settings` guard. If you set temperature or top_p on a Claude 5.5 model through OpenRouterModel, the value is forwarded to OpenRouter. With default routing OpenRouter ignores unsupported parameters; with require_parameters=true, providers that do not support them are excluded.** [medium]
  The flag is consumed in models/anthropic.py, models/bedrock.py and providers/github_copilot.py, but not in models/openrouter.py. The OpenAI-path sampling-param drop applies only to OpenAI reasoning profiles. Combining temperature with require_parameters=true on Haiku 5.5 or Sonnet 5.5 would likely leave no eligible provider, since neither lists temperature in supported_parameters. I did not test this live.
  Source: <https://openrouter.ai/docs/guides/routing/provider-selection.md>
- **The OpenRouter pricing table shows the Free plan without prompt caching, budgets and spend controls, data-policy-based routing, or management API keys; Standard (pay-as-you-go) has all of them. This partly contradicts other pages, which say key credit limits are on every plan and ZDR routing is available on every plan.** [medium]
  Buying any credits moves you to Standard, which removes the ambiguity in practice.
  Source: <https://openrouter.ai/pricing>
- **OpenRouter offers `:batch` catalog variants at 50% off for its Batch API, plus routing variants on any slug: `:floor` sorts by price and allows flex tier, `:nitro` sorts by throughput and allows priority tier, and `:exacto` routes for tool-calling quality.** [medium]
  Pydantic AI does not have a batch path for OpenRouter. The routing variants work as plain slug suffixes in the model string.
  Source: <https://openrouter.ai/docs/faq>

### Exact snippets (copied from the sources named)

**Install (Pydantic AI docs)** — <https://pydantic.dev/docs/ai/models/openrouter/>

```
uv add "pydantic-ai-slim[openrouter]"
```

**Extra definition in v2.56.0 pyproject** — <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pyproject.toml>

```
openrouter = ["openai>=3.26.0"]
```

**API key resolution in OpenRouterProvider** — <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pydantic_ai/providers/openrouter.py>

```
api_key = api_key or os.getenv('OPENROUTER_API_KEY')
if not api_key and openai_client is None:
    raise UserError(
        'Set the `OPENROUTER_API_KEY` environment variable or pass it via `OpenRouterProvider(api_key=...)`'
```

**Model string usage (docs)** — <https://pydantic.dev/docs/ai/models/openrouter/>

```
from pydantic_ai import Agent

agent = Agent('openrouter:anthropic/claude-sonnet-4.6')
```

**Auto switch to NativeOutput for thinking models** — <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pydantic_ai/models/__init__.py>

```
mode = self.profile.get('default_structured_output_mode', 'tool')
if (
    mode == 'tool'
    and model_request_parameters.output_tools
    and self.profile.get('supports_json_schema_output', False)
    and self._forced_tool_choice_disables_thinking(model_settings, model_request_parameters)
):
    return 'native'
```

**Caching via OpenRouterModelSettings (docs)** — <https://pydantic.dev/docs/ai/models/openrouter/>

```
model = OpenRouterModel('anthropic/claude-sonnet-4.6')
agent = Agent(
    model,
    instructions='You are a specialized assistant with deep domain knowledge...',
    model_settings=OpenRouterModelSettings(
        openrouter_cache_instructions=True,
        openrouter_cache_messages=True,
        openrouter_cache_tool_definitions=True,
    ),
)
```

**Suggested project defaults (assembled from field names verified in v2.56.0 source; not run live)** — <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pydantic_ai/models/openrouter.py>

```
from pydantic_ai import Agent, NativeOutput
from pydantic_ai.models.openrouter import OpenRouterModelSettings

PRIVATE = {'zdr': True, 'data_collection': 'deny'}

tutor = Agent(
    'openrouter:anthropic/claude-haiku-5.5',
    model_settings=OpenRouterModelSettings(
        openrouter_provider=PRIVATE,
        openrouter_reasoning={'effort': 'low'},
        openrouter_cache_instructions=True,
        max_tokens=4000,
    ),
)
grader = Agent(
    'openrouter:anthropic/claude-sonnet-5.5',
    output_type=NativeOutput(Grade),
    model_settings=OpenRouterModelSettings(
        openrouter_provider={**PRIVATE, 'require_parameters': True},
        openrouter_reasoning={'effort': 'low'},
        max_tokens=8000,
    ),
)
```

**Default LLM judge model (pydantic-evals)** — <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_evals/pydantic_evals/evaluators/llm_as_a_judge.py>

```
_default_model: models.Model | models.KnownModelName = 'openai:gpt-5.2'
...
def set_default_judge_model(model: models.Model | models.KnownModelName) -> None:
```

**Embedder routing for OpenAI-compatible providers (openrouter included)** — <https://github.com/pydantic/pydantic-ai/blob/v2.56.0/pydantic_ai_slim/pydantic_ai/embeddings/__init__.py>

```
if model_kind in (
    'openai',
    *get_args(OpenAIChatCompatibleProvider.__value__),
    *get_args(OpenAIResponsesCompatibleProvider.__value__),
):
    from .openai import OpenAIEmbeddingModel

    return OpenAIEmbeddingModel(model_name, provider=provider)
```

**OpenRouter API key creation body (spend cap fields)** — <https://openrouter.ai/docs/api/api-reference/api-keys/create-a-new-api-key.md>

```
POST https://openrouter.ai/api/v1/keys   (management API key)
{"name": "My New API Key", "limit": 50, "limit_reset": "monthly", "include_byok_in_limit": true, "expires_at": "2027-12-31T23:59:59Z"}
# limit_reset enum: daily | weekly | monthly ; update with PATCH /api/v1/keys/{key_hash}
```

**Check remaining key limit** — <https://openrouter.ai/docs/api_reference/limits.md>

```
GET https://openrouter.ai/api/v1/key   (Authorization: Bearer <OPENROUTER_API_KEY>) -> limit, limit_remaining, limit_reset, budgets, effective_budget
```

**Read-only catalog checks used for prices (no key needed)** — <https://openrouter.ai/api/v1/models>

```
curl -s https://openrouter.ai/api/v1/models | jq '.data[] | select(.id=="anthropic/claude-haiku-5.5") | .pricing'
curl -s https://openrouter.ai/api/v1/models/anthropic/claude-sonnet-5.5/endpoints
curl -s https://openrouter.ai/api/v1/endpoints/zdr
curl -s https://openrouter.ai/api/v1/embeddings/models
```

### Recommendations
- Pin `pydantic-ai-slim[openrouter]==2.56.0` and `pydantic-evals==2.56.0` in pyproject/uv.lock. Keep OPENROUTER_API_KEY only in a git-ignored .env and in GitHub Actions secrets, and turn on GitHub secret scanning and push protection, because the repo is public.
- Put all model slugs in one config module or env vars (TUTOR_MODEL, GRADER_MODEL, DRAFT_MODEL, JUDGE_MODEL, EMBED_MODEL) so swapping models is a one-line change.
- Tutor default: `openrouter:anthropic/claude-haiku-5.5` with openrouter_reasoning={'effort': 'low'} ($0.10/$0.50 per 1M). Keep conversation context under 100K prompt tokens to avoid Haiku 5.5's 5x long-prompt tier. Budget fallbacks: `openrouter:openai/gpt-6-luna` (same price) or `openrouter:google/gemini-3.1-flash-lite`.
- Grader default: `openrouter:anthropic/claude-sonnet-5.5` with an explicit NativeOutput(Grade) Pydantic model and effort 'low' or 'medium'. Add provider require_parameters=True so only structured-output endpoints are used. Do not set temperature (Claude 5.5 rejects it) and never send effort 'none' (Sonnet 5.5 returns a 400). To cut costs, calibrate Haiku 5.5 at effort 'medium' against Sonnet 5.5 on a labeled pydantic-evals dataset before switching.
- Content drafting default: `openrouter:anthropic/claude-sonnet-5.5` at effort 'medium'. Pydantic AI already ignores the unified thinking=False on this model, so thinking stays on.
- Evals: call `set_default_judge_model('openrouter:anthropic/claude-sonnet-5.5')` once in the evals setup, or pass model= on each LLMJudge, so judges never fall back to 'openai:gpt-5.2'. When judging Claude outputs, consider a different-family judge (for example openai/gpt-6-luna) as a cross-check.
- Spend safety for autonomous agents and auto-merge: buy a small amount of credit (the 5.5% fee applies), disable auto top-up, and create separate keys, each with `limit` and `limit_reset`: a local-dev key (for example $10/month) and, only if CI runs live evals, a CI key (for example $1/day). Monitor with GET /api/v1/key. Keep normal CI offline with TestModel/FunctionModel and `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False`.
- Privacy: in OpenRouter Settings > Privacy, turn off provider training for both paid and free models, leave I/O logging and 'use of inputs/outputs' off, and enable ZDR per model group, or pass openrouter_provider={'zdr': True, 'data_collection': 'deny'} on every request. Under Anthropic-group ZDR, Claude runs on Bedrock or Vertex, not first-party Anthropic.
- Always set max_tokens explicitly. Thinking tokens count against it, and a small cap also keeps the new-account in-flight spending budget from returning 402 when parallel subagents or eval runs fire many requests.
- Caching: give the tutor long, static instructions and enable `cache=True` (or openrouter_cache_instructions=True). Haiku 5.5 caches prompts of 512 tokens or more, and reads cost 0.1x. Until issues #7467 and #9236 are fixed, avoid placing a CachePoint as the first item of a later user prompt part, and avoid the SystemReminders capability on OpenRouter.
- Phase 2 RAG: use `Embedder('openrouter:openai/text-embedding-3-small')` ($0.02/1M; an Azure ZDR endpoint exists), and smoke-test it once against a capped key before building the pgvector schema. Fix the vector dimension in the schema and never mix embedding models in one index.
- Track cost per request from result.response.provider_details (upstream_inference_cost, downstream_provider) and OpenRouter's Activity page, because RequestUsage.cost is not filled from OpenRouter's billed cost (#7150).

### Risks
- Public repo plus autonomous agents and auto-merge: an agent could commit a key, or merge code that loops expensive Sonnet calls. A per-key `limit`, no auto top-up, and offline CI are the main safeguards.
- Default LLMJudge model is 'openai:gpt-5.2'. Without set_default_judge_model, evals fail if OPENAI_API_KEY is missing, or bill a different account if it is set.
- Haiku 5.5 pricing jumps 5x for prompts of 100K tokens or more ($0.50/$2.50), and its tokenizer uses about 30% more tokens than Haiku 4.5. Long tutoring sessions with full history can cross the threshold silently.
- Thinking is on by default for Haiku 5.5 and Sonnet 5.5, and mandatory for Sonnet 5.5. Thinking tokens are billed as output, so grader and drafting costs exceed naive estimates, and a low max_tokens can end with stop_reason max_tokens and no answer.
- Account-bound thinking replay: Pydantic AI sends prior thinking parts back. With strict provider.only, provider.ignore or ZDR settings, OpenRouter may return a 400 asking you to allow the producing provider or drop the thinking blocks. This matters most for multi-turn Sonnet 5.5 under ZDR, which leaves only Bedrock and Vertex.
- Sampling parameters (temperature, top_p) are not stripped on the OpenRouter path for Claude 5.5. They are ignored by default, but with require_parameters=True they may leave no eligible endpoint.
- In-flight spending budget: a new or low-balance account can get 402 errors under concurrency even with a positive balance.
- Restricting routing to ZDR endpoints shrinks the provider pool and may reduce availability or add latency. Regional endpoints cost about 10% more.
- OpenRouter slugs and prices change often; Haiku 5.5 was added 2026-10-07. Re-check /api/v1/models before hard-coding prices into budget logic.
- Using `openrouter_models` fallbacks across different labs can change output schema handling and caching. Keep fallbacks within one model family for graders.
- The Embedder path via 'openrouter:' is verified from source only, not live or by an official docs example.
- OpenRouter documentation is inconsistent about which features the Free plan includes (spend controls and data-policy routing). Treat Standard (credits purchased) as required.

### Open questions
- Is `Embedder('openrouter:openai/text-embedding-3-small')` confirmed to work end-to-end, including usage mapping and `dimensions`? Not run live because the task was read-only and had no key.
- Exact OpenRouter crypto-payment fee percentage: the number did not render on the FAQ page.
- Exact in-flight spending budget threshold, fraction and ceiling for new accounts; OpenRouter does not publish them.
- Does a zero-credit Free account really lack data-policy-based routing, as the pricing table says? The FAQ says ZDR routing is available on every plan.
- On Sonnet 5.5 under Anthropic-group ZDR (Bedrock and Vertex only), does OpenRouter keep multi-turn thinking replays on the producing provider, as it documents for Haiku 5.5, or return a 400? The docs only state that Sonnet 5.5 replays are never sent to Bedrock or Vertex for blocks produced in the Anthropic group.
- Does OpenRouter ignore or reject a temperature value sent to Haiku 5.5 or Sonnet 5.5 under default routing? The docs say unsupported parameters are ignored, but Anthropic upstream rejects non-default temperature.
- How do Haiku 5.5, gpt-6-luna and Gemini Flash-Lite compare on this app's tutoring and rubric-grading tasks? This needs a small pydantic-evals dataset; I did not check public benchmarks.
- Does genai-prices (used by Pydantic AI usage cost) have entries for OpenRouter's Claude 5.5 and gpt-6-luna slugs? Not checked.
