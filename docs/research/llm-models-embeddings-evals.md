# LLM models, prices, embeddings, tracing and evals

_Research archive. Checked against primary sources on 2026-10-14. Facts about fast-moving tools (Claude Code, Pydantic AI, FastAPI, GitHub, OpenRouter) go stale quickly: re-check before relying on a number._

- **Needed by:** Phase 1 (models, evals); Phase 2 (embeddings)
- **Licence / attribution notes:** Vendor pricing pages cited by link.
- **Covers:** Claude/OpenAI/Gemini prices, Claude 5.5 behaviour changes, embedding models and pgvector limits, Logfire, testing and pydantic-evals, cost estimates

## LLM, embeddings, tracing and evals for a Pydantic AI learning app (models and prices, embeddings, Logfire/OTel, testing and evals, RAG with citations, cost estimates)

**Summary.** As of 2026-10-14, the cheapest Claude is claude-haiku-5-5 at $0.10 input / $0.50 output per 1M tokens for prompts up to 100K tokens; above that it costs $0.50 / $2.50. The mid tier is claude-sonnet-5-5 at $2 / $10. Batch requests are 50% off on both, and cache reads cost 0.1x of input (0.05x on Sonnet 5.5). Comparable non-Claude small models: OpenAI gpt-6-luna ($0.10 / $0.50), gpt-5-mini ($0.25 / $2.00) and gpt-5-nano ($0.05 / $0.40); Gemini 3.1 Flash-Lite ($0.25 / $1.50) and 2.5 Flash-Lite ($0.10 / $0.40). Gemini 3.6/3.8 Flash cost $0.75 / $3.75 and double on Jan 1, 2027. Pydantic AI is now v2.56.0 (released 2026-10-13) and its docs moved to pydantic.dev/docs/ai. It already knows the claude-*-5-5 model IDs and has a first-class Embedder API for OpenAI, Google, Cohere, VoyageAI, Bedrock and sentence-transformers. It also works around a new restriction on Sonnet 5.5 and Opus 5.5: forced tool_choice is rejected, so Pydantic AI switches to 'auto', and it drops temperature/top_p settings with a warning. For embeddings, the best fit is the Voyage 4 family: 1024 dimensions by default (well under pgvector's 2000-dimension HNSW limit for vector), 32K context, $0.02-$0.12 per 1M tokens, and 200M free tokens per account. OpenAI text-embedding-3-small (1536 dimensions, $0.02/M) is the one-key fallback. For tracing, the Logfire Personal plan is free: 10M records/month, 30-day retention, and a hard cap that pauses ingestion instead of billing. Logfire has one-line instrumentation for Pydantic AI, FastAPI and psycopg and a hosted MCP server; the old local stdio server's repo is archived. Langfuse (free tier 50k units/month) or plain OpenTelemetry also work, because Pydantic AI emits standard GenAI OTel spans. For testing, use TestModel/FunctionModel with models.ALLOW_MODEL_REQUESTS=False. pydantic-evals 2.56.0 provides Dataset/Case/LLMJudge, YAML datasets with a generated JSON schema, repeat=, max_concurrency= and baseline comparison. LLMJudge defaults to openai:gpt-5.2, so set the judge model explicitly. Rough costs: about $0.10 per 100 tutor messages on Haiku 5.5 or about $2 on Sonnet 5.5, about $0.08 or $1.50 per 100 graded answers, and $0.02-$0.25 for a full re-embed of 3-6 MB of Markdown. That re-embed is $0 on Voyage's free tokens.

### Findings

- **Current Claude API model IDs and standard prices per 1M tokens (input/output): claude-haiku-5-5 $0.10/$0.50 for prompts up to 100K tokens and $0.50/$2.50 above 100K; claude-sonnet-5-5 $2/$10; claude-opus-5-5 $4/$20; legacy claude-haiku-4-5 $1/$5; claude-sonnet-4-6 $3/$15.** [high, load-bearing]
  Haiku 5.5 is priced per request by total prompt length, cache reads and writes included, so keep RAG prompts well under 100K. All four current models have 1M context, 128K max output and a reliable knowledge cutoff of Jun 2026. Haiku 5.5 retirement is not before Oct 7, 2027; Sonnet 5.5 not before Sep 28, 2027. Model IDs are dateless pinned snapshots, so never append dates.
  Source: <https://platform.claude.com/docs/en/about-claude/pricing>
- **Anthropic discounts: Batch API is 50% off input and output (Haiku 5.5 batch $0.05/$0.25). Cache reads are 0.1x base input (0.05x on Sonnet 5.5 and Opus 5.5), 5-minute cache writes are 1.25x and 1-hour writes are 2x. Batch and caching discounts stack.** [high, load-bearing]
  Minimum cacheable prefix is 512 tokens for Haiku 5.5 and Sonnet 5.5, versus 4,096 for Haiku 4.5. Shorter prefixes are silently not cached. A request allows at most 4 cache breakpoints. Claude 4.7+ models use a newer tokenizer that produces about 30% more tokens for the same text.
  Source: <https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md>
- **Behavior changes on current Claude models that affect Pydantic AI settings. Haiku 5.5: thinking on by default, default effort 'medium'. Sonnet 5.5: thinking on, default effort 'high'. Sonnet 5.5 and Opus 5.5 reject forced tool_choice ('any'/'tool'). Haiku 5.5, Sonnet 5.x and Opus 4.7+ reject temperature/top_p/top_k.** [high, load-bearing]
  Pydantic AI handles both restrictions. When the profile marks a model as not supporting forced tool_choice, Pydantic AI sends 'auto' for output tools, and an explicit tool_choice='required' raises UserError. It drops sampling settings with a warning. Consequence: you cannot get a deterministic temperature=0 judge on these models. Thinking tokens are billed as output tokens.
  Source: <https://github.com/pydantic/pydantic-ai/blob/main/pydantic_ai_slim/pydantic_ai/profiles/anthropic.py>
- **Pydantic AI latest release is v2.56.0 (2026-10-13). Docs moved from ai.pydantic.dev to pydantic.dev/docs/ai/ (301 redirects). KnownModelName includes 'anthropic:claude-haiku-5-5', 'anthropic:claude-sonnet-5-5' and 'anthropic:claude-opus-5-5'.** [high, load-bearing]
  Anthropic prompt caching is configured through AnthropicModelSettings keys anthropic_cache_instructions, anthropic_cache_tool_definitions, anthropic_cache_messages and anthropic_cache, each taking True, '5m' or '1h'. A provider-agnostic model_settings={'cache': True} is also available. result.usage exposes cache_write_tokens and cache_read_tokens. Tutorials written for 0.x/1.x may be stale.
  Source: <https://pydantic.dev/docs/ai/models/anthropic/>
- **OpenAI small-model Standard prices per 1M tokens (input / cached input / output): gpt-6-luna $0.10/$0.01/$0.50, gpt-5.6-luna $0.20/$0.02/$1.20, gpt-5.4-mini $0.75/$0.075/$4.50, gpt-5.4-nano $0.20/$0.02/$1.25, gpt-5-mini $0.25/$0.025/$2.00, gpt-5-nano $0.05/$0.005/$0.40, gpt-4.1-nano $0.10/$0.025/$0.40. Batch tier is exactly half.** [high]
  The docs moved from platform.openai.com/docs/pricing to developers.openai.com/api/docs/pricing. The flagship gpt-6-astra costs $10/$50.
  Source: <https://developers.openai.com/api/docs/pricing>
- **Gemini Flash paid prices per 1M text tokens (input/output): gemini-3.1-flash-lite $0.25/$1.50, gemini-2.5-flash-lite $0.10/$0.40, gemini-3.5-flash-lite $0.30/$2.50, gemini-3-flash-preview $0.50/$3.00, gemini-2.5-flash $0.30/$2.50. gemini-3.6-flash and gemini-3.8-flash cost $0.75/$3.75 and rise to $1.50/$7.50 on Jan 1, 2027. Batch is about half.** [medium]
  The page also shows a free tier for these models. Context caching is extra and includes a storage charge per 1M tokens per hour.
  Source: <https://ai.google.dev/gemini-api/docs/pricing>
- **Pydantic AI has a first-class embeddings API. Embedder offers embed_query, embed_documents, count_tokens and max_input_tokens, and EmbeddingSettings(dimensions=..., truncate=...) sets options. Supported providers: OpenAI (and compatible APIs, including Azure, Ollama and vLLM), Google, Cohere, VoyageAI, Bedrock and Sentence Transformers. TestEmbeddingModel is available for tests.** [high, load-bearing]
  Model strings: 'openai:text-embedding-3-small', 'google:gemini-embedding-001', 'cohere:embed-v4.0', 'voyageai:voyage-3.5', 'bedrock:amazon.titan-embed-text-v2:0', 'ollama:nomic-embed-text'. The source's Voyage literal list includes voyage-4-large, voyage-4 and voyage-4-lite. Instrument with Embedder(..., instrument=True). ALLOW_MODEL_REQUESTS=False also blocks embedding calls. No reranker abstraction was found, so call rerank APIs directly.
  Source: <https://pydantic.dev/docs/ai/guides/embeddings/>
- **Voyage 4 embeddings: voyage-4-large $0.12/M, voyage-4 $0.06/M, voyage-4-lite $0.02/M, with 200M free tokens per account. All have 32K context, default 1024 dimensions, output_dimension options 256/512/1024/2048, and output_dtype float/int8/uint8/binary/ubinary. The 4-series models share one embedding space.** [medium, load-bearing]
  voyage-code-4 ($0.12/M) is recommended for code. Older voyage-3.5 ($0.06) and 3.5-lite ($0.02) are listed without free tokens. The Batch API is 33% off but does not draw on free tokens. Because the 4-series is mutually compatible, you can embed documents with voyage-4-large and queries with voyage-4-lite. The pricing page has internal inconsistencies about which models get free tokens.
  Source: <https://docs.voyageai.com/docs/embeddings>
- **OpenAI embeddings: text-embedding-3-small is 1536 dimensions at $0.02/M, text-embedding-3-large is 3072 dimensions at $0.13/M, both with 8192 max input tokens. The dimensions parameter shortens output; 3-large exceeds pgvector's HNSW 'vector' limit unless shortened to 2000 or fewer, or stored as halfvec.** [high, load-bearing]
  MTEB scores: 3-small 62.3%, 3-large 64.6%. The page lists no embedding model newer than text-embedding-3, and no batch embedding price.
  Source: <https://developers.openai.com/api/docs/guides/embeddings>
- **Gemini embedding: gemini-embedding-2 costs $0.20/M text tokens ($0.10 batch) and has a free tier. Both gemini-embedding-2 and -001 default to 3072 dimensions with output_dimensionality from 128 to 3072 (recommended 768/1536/3072). Input limit is 8,192 tokens for -2 and 2,048 for -001. task_type is not supported on -2.** [high]
  gemini-embedding-2 auto-renormalizes non-default dimensions; -001 needs manual normalization. Pick 768 or 1536 for pgvector HNSW.
  Source: <https://ai.google.dev/gemini-api/docs/embeddings>
- **Cohere embed-v4.0 has 128K context, default 1536 dimensions (256/512/1024/1536). The newer embed-v5.0-pro/fast default to 2048 dimensions. Cohere's official pricing page no longer lists per-token Embed prices or per-search Rerank prices.** [low]
  Third-party sources quote embed-v4 at about $0.12/M text tokens and Rerank 3.5 / Rerank 4 Fast at about $2.00 per 1K searches; these are unverified. Trial keys are free but rate-limited and not allowed for production.
  Source: <https://docs.cohere.com/docs/cohere-embed>
- **pgvector storage and index limits: vector and halfvec store up to 16,000 dimensions. HNSW and IVFFlat index vector up to 2,000 dimensions, halfvec up to 4,000 and bit up to 64,000; HNSW indexes sparsevec up to 1,000 non-zero elements. hnsw.ef_search defaults to 40.** [high, load-bearing]
  The README recommends 'Reciprocal Rank Fusion or a cross-encoder' to combine full-text and vector results for hybrid search. The latest pgvector tag is v0.8.7. Neon's extension page uses 0.8.0 as its example 'latest' version, so check the Neon extensions page for the exact version. Neon advises keeping maintenance_work_mem for HNSW builds at or below 50-60% of compute RAM.
  Source: <https://github.com/pgvector/pgvector>
- **Logfire pricing. Personal: free, 10M records/month, 30-day retention, 1 seat, 3 projects, hard cap where ingestion pauses (no overage). Team: $49/month, 10M included, $2 per extra million, 5 seats. Growth: $249/month, up to 90-day retention.** [high, load-bearing]
  Records are spans, logs and metrics combined. Personal is allowed in production. The Logfire SDK and Pydantic AI are both MIT-licensed.
  Source: <https://pydantic.dev/pricing>
- **Instrumentation entry points: logfire.configure(), logfire.instrument_pydantic_ai(), logfire.instrument_fastapi(app) (needs 'logfire[fastapi]'), logfire.instrument_psycopg() (needs 'logfire[psycopg]'; call once, after configuring connections) and logfire.instrument_httpx(capture_all=True). logfire.force_flush() and logfire.shutdown() exist in the SDK.** [high, load-bearing]
  InstrumentationSettings(include_content=False) strips prompt and completion content, which is useful for learner privacy. The default instrumentation version is 5. The logfire package is at 5.2.0. On Vercel serverless, spans may be lost if the batch processor has not flushed before the function freezes, so call force_flush at request end. That flush behavior is not documented by Logfire for Vercel.
  Source: <https://pydantic.dev/docs/ai/integrations/logfire/index.md>
- **The Logfire MCP server is now remote: https://logfire-us.pydantic.dev/mcp (EU: https://logfire-eu.pydantic.dev/mcp). It authenticates with browser OAuth by default, or with a Bearer API key that has project:read scope. The old pydantic/logfire-mcp stdio repo is archived.** [high, load-bearing]
  Tools include query_run, query_schema_reference, query_find_exceptions_in_file, project_list, plus dashboard_*, alert_*, issue_list and local_dev_session.
  Source: <https://pydantic.dev/docs/logfire/guides/mcp-server/>
- **Alternatives to Logfire. Pydantic AI emits OpenTelemetry GenAI-convention spans to any backend, either via logfire.configure(send_to_logfire=False) with OTEL_EXPORTER_OTLP_ENDPOINT, or with no Logfire at all via TracerProvider plus Agent.instrument_all(). Langfuse Cloud Hobby is free with 50k units/month (traces, observations and scores all count), 30-day access and 2 users; Core is $29 for 100k units.** [medium]
  The Langfuse repo is MIT except the ee/ directories, and its copyright holder is now ClickHouse, Inc. Self-hosting Langfuse means running ClickHouse, Postgres, Redis and S3 (from general knowledge, not verified), which is heavy for a low-RAM Mac. At about 10 observations per tutor message, the Langfuse free tier covers roughly 5k messages/month; Logfire's covers far more.
  Source: <https://langfuse.com/pricing>
- **Pydantic AI unit testing: set models.ALLOW_MODEL_REQUESTS = False, swap models with agent.override(model=TestModel()) or FunctionModel(fn), inspect runs with capture_run_messages(), and use dirty-equals (IsNow, IsStr) and inline-snapshot for assertions.** [high]
  The pydantic-ai repo itself uses anyio_mode='auto', inline-snapshot>=0.32.5 and dirty-equals>=0.9.0. It now records and replays provider HTTP traffic with 'cassetter' (Kludex, Rust-based, 0.14.0) instead of pytest-recording. pytest-recording 0.14.0 (VCR.py) still works for this. Record cassettes once locally with real keys, then replay offline in CI and scrub API keys from headers.
  Source: <https://pydantic.dev/docs/ai/guides/testing/>
- **pydantic-evals (2.56.0): Dataset(name=, cases=[Case(name, inputs, expected_output, metadata)], evaluators=[...]), run with dataset.evaluate_sync(task, max_concurrency=N) or await dataset.evaluate(...). It supports repeat=, retry_task=, retry_evaluators= and report.print(include_input=..., baseline=other_report).** [high, load-bearing]
  to_file('x.yaml') also writes x_schema.json and adds a '# yaml-language-server: $schema=...' header for VS Code autocomplete. Load with Dataset[...].from_file(path, custom_evaluator_types=[...]). generate_dataset(dataset_type=..., n_examples=..., extra_instructions=...) can draft cases. Install with 'pydantic-evals' or 'pydantic-evals[logfire]'.
  Source: <https://pydantic.dev/docs/ai/evals/how-to/dataset-management/>
- **LLMJudge (from pydantic_evals.evaluators) takes rubric, model, include_input, include_expected_output, score={'include_reason': True}, assertion and model_settings. Its default judge model is 'openai:gpt-5.2', which can be changed with set_default_judge_model().** [high, load-bearing]
  If the judge model is not set, LLMJudge silently needs OPENAI_API_KEY. The docs example uses model_settings temperature=0.0, but Pydantic AI drops temperature for Haiku 5.5 and Sonnet 5.x, so consistency has to come from rubric design and repeat= rather than temperature.
  Source: <https://pydantic.dev/docs/ai/evals/evaluators/llm-judge/>
- **Structured citations. Pydantic AI output_type accepts a Pydantic model and has three modes: ToolOutput (default), NativeOutput (provider JSON schema) and PromptedOutput. @agent.output_validator can check output against ctx.deps and raise ModelRetry; the output retry budget defaults to 1 and is set with retries={'output': N}.** [medium, load-bearing]
  Pydantic AI's Anthropic profile marks claude-sonnet-5*, claude-haiku-5-5 and claude-opus-5* as supporting JSON-schema output, so NativeOutput is available. Because forced tool_choice is rejected on Sonnet 5.5, NativeOutput is the more reliable mode for a citation schema there. Anthropic's own document 'citations' feature cannot be combined with output_config.format, per the bundled claude-api skill notes (not re-verified on the live docs), so implement chunk-ID citations yourself.
  Source: <https://pydantic.dev/docs/ai/core-concepts/output/>
- **Hybrid retrieval and reranking evidence. In Anthropic's contextual retrieval post, top-20 retrieval failure fell 35% with contextual embeddings, 49% with contextual embeddings plus BM25, and 67% with reranking added (5.7% to 1.9%). Chunks are 'a few hundred tokens' (800 in the cost model), passing the top 20 chunks worked best, and reranking took the top 150 down to 20. Voyage rerankers: rerank-3 $0.05/M and rerank-3-lite $0.02/M, with 200M free tokens, 32K context, and at most 1,000 documents per request.** [high]
  Voyage bills reranking as query_tokens x number_of_docs + sum(doc_tokens); for example, 40 candidates x 400 tokens comes to about 17K tokens, roughly $0.0003-0.0009 per query. The pgvector-python RRF example uses k=60 with a FULL OUTER JOIN of vector-rank and ts_rank_cd rank. I found no Anthropic chunk-size rule for Markdown; third-party guidance is to split on headings and start around 300-800 tokens.
  Source: <https://www.anthropic.com/news/contextual-retrieval>
- **Rough costs (my estimates, using the official prices above). Tutor message: about 6K input tokens (1.5K cacheable instructions, 8 chunks of about 400 tokens, history, question) and about 800 output tokens including thinking. That gives Haiku 5.5 about $0.10-0.13 per 100 messages; Sonnet 5.5 about $1.75-2.00; gpt-5-mini about $0.31; gpt-6-luna about $0.10; gemini-3.1-flash-lite about $0.27. Graded answer: about 2.5K input and 1K output, giving Haiku 5.5 about $0.08 per 100 and Sonnet 5.5 about $1.50 per 100.** [medium]
  Full re-embed: 3-6 MB of Markdown is about 0.8-1.7M tokens (3.5-4 characters/token), about 1-2M with breadcrumbs and overlap. Cost: text-embedding-3-small or voyage-4-lite $0.02-0.04; voyage-4 $0.06-0.12; voyage-4-large or text-embedding-3-large $0.12-0.26; gemini-embedding-2 $0.20-0.40. All Voyage 4 costs are $0 within the 200M free tokens. Quiz generation on Sonnet 5.5 is about $0.04 per lesson (5K in, 3K out), about $0.02 with Batch. If retrieval runs as an agent tool, which needs two model requests, multiply the tutor cost by about 1.7.
  Source: <https://platform.claude.com/docs/en/about-claude/pricing>

### Exact snippets (copied from the sources named)

**Pydantic AI Embedder with reduced dimensions (verbatim)** — <https://pydantic.dev/docs/ai/guides/embeddings/>

```python
from pydantic_ai import Embedder
from pydantic_ai.embeddings import EmbeddingSettings

embedder = Embedder(
    'openai:text-embedding-3-small',
    settings=EmbeddingSettings(dimensions=256),
)
```

**Logfire + Pydantic AI instrumentation (verbatim)** — <https://pydantic.dev/docs/ai/integrations/logfire/index.md>

```python
import logfire

from pydantic_ai import Agent

logfire.configure()
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)  # (1)

agent = Agent('openai:gpt-5.2')
result = agent.run_sync('What is the capital of France?')
print(result.output)
#> The capital of France is Paris.
```

**Logfire FastAPI + psycopg instrumentation (verbatim lines from two doc pages)** — <https://pydantic.dev/docs/logfire/integrations/databases/psycopg/>

```python
# pip install 'logfire[fastapi]'   /   pip install 'logfire[psycopg]'
import logfire

logfire.configure()
logfire.instrument_fastapi(app)

# psycopg page:
logfire.instrument_psycopg()  # instrument whichever of psycopg/psycopg2 is installed
```

**Send Pydantic AI traces to another OTel backend instead of Logfire (verbatim excerpt)** — <https://pydantic.dev/docs/ai/integrations/logfire/index.md>

```python
os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = 'http://localhost:4318'  # (1)
logfire.configure(send_to_logfire=False)  # (2)
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)
```

**Logfire remote MCP server for Claude Code and VS Code (verbatim)** — <https://pydantic.dev/docs/logfire/guides/mcp-server/>

```bash
claude mcp add --transport http logfire https://logfire-us.pydantic.dev/mcp
claude mcp login logfire

# .vscode/mcp.json
{
  "servers": {
    "logfire": {
      "type": "http",
      "url": "https://logfire-us.pydantic.dev/mcp"
    }
  }
}
```

**pgvector HNSW index + hybrid search with Reciprocal Rank Fusion (verbatim from pgvector README and pgvector-python examples/hybrid_search/rrf.py)** — <https://github.com/pgvector/pgvector-python/blob/master/examples/hybrid_search/rrf.py>

```sql
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops);

WITH semantic_search AS (
    SELECT id, RANK () OVER (ORDER BY embedding <=> %(embedding)s) AS rank
    FROM documents
    ORDER BY embedding <=> %(embedding)s
    LIMIT 20
),
keyword_search AS (
    SELECT id, RANK () OVER (ORDER BY ts_rank_cd(to_tsvector('english', content), query) DESC)
    FROM documents, plainto_tsquery('english', %(query)s) query
    WHERE to_tsvector('english', content) @@ query
    ORDER BY ts_rank_cd(to_tsvector('english', content), query) DESC
    LIMIT 20
)
SELECT
    COALESCE(semantic_search.id, keyword_search.id) AS id,
    COALESCE(1.0 / (%(k)s + semantic_search.rank), 0.0) +
    COALESCE(1.0 / (%(k)s + keyword_search.rank), 0.0) AS score
FROM semantic_search
FULL OUTER JOIN keyword_search ON semantic_search.id = keyword_search.id
ORDER BY score DESC
LIMIT 5
-- example uses k = 60
```

**pydantic-evals minimal Dataset + run + LLMJudge (verbatim pieces)** — <https://pydantic.dev/docs/ai/evals/>

```python
from pydantic_evals import Case, Dataset

case1 = Case(
    name='simple_case',
    inputs='What is the capital of France?',
    expected_output='Paris',
    metadata={'difficulty': 'easy'},
)

dataset = Dataset(name='capital_quiz', cases=[case1])

report = dataset.evaluate_sync(guess_city)
report.print(include_input=True, include_output=True, include_durations=False)

# concurrency page:
report = dataset.evaluate_sync(my_task, max_concurrency=5)

# LLM judge page:
from pydantic_evals.evaluators import LLMJudge
LLMJudge(
    rubric='Response quality',
    score={'include_reason': True},
    assertion=False,
)
```

**Pydantic AI test fixture blocking real LLM calls (assembled from verbatim doc lines)** — <https://pydantic.dev/docs/ai/guides/testing/>

```python
from pydantic_ai import models, capture_run_messages, RequestUsage
from pydantic_ai.models.test import TestModel
from pydantic_ai.models.function import AgentInfo, FunctionModel

pytestmark = pytest.mark.anyio
models.ALLOW_MODEL_REQUESTS = False

@pytest.fixture
def override_weather_agent():
    with weather_agent.override(model=TestModel()):
        yield

async def test_forecast(override_weather_agent: None):
    ...
```

### Recommendations
- Tutor chat (RAG + citations): use 'anthropic:claude-haiku-5-5' with effort 'low' or 'medium', AnthropicModelSettings(anthropic_cache_instructions=True, anthropic_cache_tool_definitions=True), and a static instructions block of at least 512 tokens so it caches. Retrieve before the model call and inject the chunks, rather than exposing search as a tool; that means one request per message instead of two. Escalate to 'anthropic:claude-sonnet-5-5' only for 'think deeper' follow-ups, or if evals show weak citation faithfulness.
- Quiz generation: use 'anthropic:claude-sonnet-5-5' offline, once per lesson, with NativeOutput into a strict Pydantic schema (exactly one correct option, distractor rationale, a source_chunk_ids list). Store the results in Postgres and review them by hand. Generation-time cost is negligible (about $0.04 per lesson), so skip the Batch API complexity unless you regenerate everything often.
- Rubric grading (LLM-as-judge): use 'anthropic:claude-sonnet-5-5' with NativeOutput: per-criterion scores, a short evidence quote from the student answer, and feedback. Keep the rubric and reference answer in a cached prefix. temperature cannot be set on these models, so get stability from explicit scoring anchors per level, and measure agreement against 20-30 hand-graded answers with a custom pydantic-evals Evaluator.
- Embeddings: use Voyage 'voyageai:voyage-4' or 'voyageai:voyage-4-lite' at 1024 dimensions in a vector(1024) column with an HNSW vector_cosine_ops index. The 200M free tokens make all re-embeds free. Because the 4-series shares one embedding space, you can later embed documents with voyage-4-large and keep queries on voyage-4-lite. Fallback if you want one fewer account: 'openai:text-embedding-3-small' with vector(1536). Store embedding_model and dimensions on each row so a model switch is an explicit migration.
- Chunking: split Markdown on H2/H3 headings. Keep code blocks intact. Target about 300-800 tokens per chunk, and split oversized sections by paragraph with about 10-15% overlap. Prepend a breadcrumb ('FastAPI > Tutorial > Dependencies') to the text you embed. Store doc_url#anchor, a content sha256 and the source commit. During the scheduled re-sync, re-embed only chunks whose hash changed.
- Hybrid search: add a generated tsvector column with a GIN index next to the HNSW index. Take the top 20 from each and fuse them with RRF (k=60), as in the pgvector-python example. Optionally rerank the top 30-40 with Voyage rerank-3-lite (free tier). Pass 6-8 chunks to the model.
- Citations: set output_type to TutorAnswer(answer: str, citations: list[Citation(chunk_id: str, quote: str)]) and keep the retrieved chunk ids in deps. Add an @agent.output_validator that raises ModelRetry if a chunk_id is not in the retrieved set or the quote is not a substring of that chunk, and set retries={'output': 2}. Render the citation links server-side from the chunk table, never from URLs the model writes.
- Tracing: use the Logfire Personal plan (free, hard-capped) with instrument_pydantic_ai, instrument_fastapi, instrument_psycopg and Embedder(instrument=True). Set InstrumentationSettings(include_content=False) in production if learners' text is sensitive. Call logfire.force_flush() at the end of requests on Vercel. Add the remote Logfire MCP server to Claude Code so you can debug traces from the terminal.
- Testing and CI: in conftest.py, set models.ALLOW_MODEL_REQUESTS=False and use TestModel/FunctionModel and TestEmbeddingModel for unit tests that run on every PR. Use a few cassette-recorded integration tests (pytest-recording/VCR or cassetter) with scrubbed headers. Keep pydantic-evals datasets as YAML under evals/ (tutor, quiz, grader). Run them in GitHub Actions only on workflow_dispatch, a 'run-evals' PR label, or nightly, with max_concurrency=2-4, 20-50 cases and an explicitly set judge model. That costs well under $1 per run. Compare runs with report.print(baseline=...).
- Configuration: keep all model IDs (tutor, grader, quizgen, judge, embedder) in one settings module or environment variables, never inline in code. They change every few months, and Gemini Flash prices change on 2027-01-01.

### Risks
- Model churn: Claude 5.5-generation models launched in Sept-Oct 2026, and Pydantic AI ships near-weekly (v2.55 on 10-09, v2.56 on 10-13). Pin pydantic-ai and anthropic versions in the lockfile and re-check model profiles when upgrading.
- Sonnet 5.5 and Opus 5.5 reject forced tool_choice. Pydantic AI silently falls back to 'auto' for ToolOutput, so the model can answer in plain text instead of calling the output tool. Prefer NativeOutput for structured outputs on these models, and avoid an explicit tool_choice='required', which raises UserError.
- Thinking is on by default on Haiku 5.5 and Sonnet 5.5, and thinking tokens bill as output. The newer tokenizer also produces about 30% more tokens. Real costs can be 1.5-2x a naive estimate, so log result.usage and check it.
- Haiku 5.5 pricing jumps 5x for prompts over 100K tokens (cache reads included). Cap retrieved context and chat history.
- LLMJudge defaults to 'openai:gpt-5.2'. Without an explicit model, evals fail without an OpenAI key, or quietly bill a second provider.
- Judges cannot run at temperature=0 on current Claude models because sampling params are dropped. Score variance between runs can make CI eval gates flaky. Use repeat= and thresholds rather than exact matches.
- Embedding dimension lock-in: the HNSW index on vector is limited to 2,000 dimensions. text-embedding-3-large (3072) and Gemini embedding defaults (3072) need truncation or halfvec. Switching models means a new column, a new index and a full re-embed.
- Logfire Personal pauses ingestion at 10M records/month instead of billing, which can leave silent gaps in traces. Serverless function freeze on Vercel can drop unflushed spans.
- Vendor-page inconsistencies: Voyage free-token eligibility differs between tables on the same page, and Cohere's official page no longer shows per-token prices. Check the dashboard before relying on free tiers.
- Anthropic's native document citations cannot be combined with structured outputs (per the claude-api skill notes; not re-verified on the live docs). Mixing them yields a 400, so the custom chunk-id citation approach is the safer design.

### Open questions
- Does Pydantic AI v2.56 expose Anthropic's Message Batches API? Not verified. If not, use the anthropic SDK directly for any batched quiz generation or offline grading.
- Is Haiku 5.5 good enough at faithful, cited answers over FastAPI/Pydantic docs, or is Sonnet 5.5 needed for the tutor? This needs a 30-50 case pydantic-evals run comparing the two.
- What are Cohere's current official per-token Embed v4/v5 and per-search Rerank 4 prices? The official page lists none, and third-party sources show about $0.12/M and $2 per 1K searches.
- Which pgvector version does Neon currently ship? The docs example says 0.8.0, while upstream is at 0.8.7. Does Neon offer pg_search (BM25) on the free plan as an alternative to tsvector full-text search?
- Does Vercel's Python runtime keep the process alive long enough for the OTel batch exporter to flush, or is logfire.force_flush() needed at the end of every request? Logfire documents nothing Vercel-specific.
- How does the gpt-6-luna model (same price as Haiku 5.5) compare in quality? It is unverified, and it would add a second provider and API key.
- What exactly does the Gemini free tier allow (rate limits, data use for training) for gemini-3.x Flash and gemini-embedding-2? Free-tier data-use terms may matter for learner content.

### Fact-check (second agent re-read the sources)

I checked these on 2026-10-14 against live sources: platform.claude.com .md docs (pricing, models overview, model IDs, deprecations, prompt caching, the Haiku/Sonnet/Opus 5.5 pages, citations), raw pydantic-ai main source (profiles/anthropic.py, models/anthropic.py, _tool_choice.py, _known_model_names.py, settings.py, usage.py, embeddings/voyageai.py, pydantic_evals dataset and reporting, llm_as_a_judge.py), PyPI (pydantic-ai and pydantic-evals 2.56.0, logfire 5.2.0, MIT), pydantic.dev docs .md pages, ai.google.dev pricing, Voyage docs and pricing, OpenAI embeddings guide and pricing, Cohere docs and pricing, the pgvector README and git tags, Neon's pgvector page, and the Langfuse pricing, billable-units page and LICENSE.

Only one claim needed a correction: the psycopg 'after configuring connections' wording. Call instrument_psycopg() after logfire.configure(), and before you open DB connections when instrumenting the module.

The Cohere pricing HTML has a stray Embed 4 '$2.50 / 1M tokens' card in its CMS data. It does not render in the retrieval tab, so it is not a real published price.

The Anthropic docs do not explicitly list Opus 4.7 as rejecting sampling params on the pages I checked. That part rests on the Pydantic AI profile, which says so.

The scratch downloads are under (session scratchpad)

Corrections:
- [corrected] Instrumentation: instrument_fastapi(app) needs logfire[fastapi]. instrument_psycopg() needs logfire[psycopg]; call it once, after configuring connections. instrument_httpx(capture_all=True), force_flush() and shutdown() exist. include_content=False works, the default version is 5, and logfire is at 5.2.0. → The psycopg ordering is misread. The docs say logfire.configure() must run before instrument_psycopg() ('Configure the connection first' means Logfire's connection to your project), and call it exactly once. In the docs example, logfire.instrument_psycopg() is called BEFORE psycopg.connect(), so module-level instrumentation should happen before DB connections are created, not after. Everything else checks out: the fastapi and psycopg extras, capture_all, force_flush(timeout_millis=3000), shutdown(), include_content=False, default version=5, and logfire 5.2.0. (<https://pydantic.dev/docs/logfire/integrations/databases/psycopg/>)

Snippet checks:
- Snippet 1 (Embedder dimensions=256): none. It matches the openai_dimensions.py example verbatim.
- Snippet 2 (Logfire + Pydantic AI + httpx): none. It is verbatim.
- Snippet 3 (FastAPI + psycopg): the call names and extras are correct, but `app` is undefined in the excerpt (it needs `from fastapi import FastAPI; app = FastAPI()`). psycopg2 users need the 'logfire[psycopg2]' extra instead. In the source, instrument_psycopg() comes after logfire.configure() and before psycopg.connect(). The FastAPI lines come from https://pydantic.dev/docs/logfire/integrations/web-frameworks/fastapi/, not the cited psycopg URL.
- Snippet 4 (OTel backend): it is a verbatim excerpt but omits `import os` and `import logfire`, which the source has. The env var must be set before logfire.configure(), as shown.
- Snippet 5 (Logfire remote MCP): none. The claude mcp add/login commands and the VS Code {"servers": {"logfire": {"type": "http", "url": ...}}} block match the docs.
- Snippet 6 (pgvector RRF): the SQL is verbatim from rrf.py, but the HNSW index line (README) targets table `items` while the query uses `documents`. Rename one so the index applies. rrf.py also creates `CREATE INDEX ON documents USING GIN (to_tsvector('english', content))`, which the snippet omits, and binds k=60 as a parameter.
- Snippet 7 (pydantic-evals): field and parameter names match the docs and source (Case name/inputs/expected_output/metadata, Dataset name/cases, evaluate_sync max_concurrency, report.print include_input/include_output/include_durations, and LLMJudge rubric/score/assertion). `guess_city` and `my_task` are undefined in the excerpt.
- Snippet 8 (testing fixture): it is missing `import pytest` and `from weather_app import weather_agent`, both present in the docs. capture_run_messages, RequestUsage, AgentInfo and FunctionModel are imported but unused. The doc's fixture example itself does not include the pytestmark or ALLOW_MODEL_REQUESTS lines; those come from the other test examples, and they are valid.
