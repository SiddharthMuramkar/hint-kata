"""Embeddings through Pydantic AI's Embedder (OpenRouter by default; see EMBED_MODEL).

Texts go out in batches of at most 64. A transient failure (rate limit, 5xx, dropped connection) is
retried once. Tests use `TestEmbeddingModel`; nothing here calls the network by itself.
"""

import time
from collections.abc import Callable, Sequence

from pydantic_ai import Embedder
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.providers.openrouter import OpenRouterProvider

from app.config import settings

BATCH = 64
RETRY_AFTER_S = 2.0
TRANSIENT = {408, 409, 425, 429, 500, 502, 503, 504}


def make_embedder(model: str | None = None) -> Embedder:
    """An Embedder for EMBED_MODEL. With an `openrouter:` model and OPENROUTER_API_KEY set in the
    local env file, the key is passed in directly (pydantic-settings does not export it)."""
    name = model or settings.embed_model
    if name.startswith("openrouter:") and settings.openrouter_api_key:
        provider = OpenRouterProvider(
            api_key=settings.openrouter_api_key, app_title=settings.openrouter_app_title
        )
        return Embedder(OpenAIEmbeddingModel(name.removeprefix("openrouter:"), provider=provider))
    return Embedder(name)


def _is_transient(e: ModelAPIError) -> bool:
    return not isinstance(e, ModelHTTPError) or e.status_code in TRANSIENT


def _embed_batch(
    embedder: Embedder, batch: Sequence[str], sleep: Callable[[float], None]
) -> list[list[float]]:
    try:
        result = embedder.embed_documents_sync(batch)
    except ModelAPIError as e:
        if not _is_transient(e):
            raise
        sleep(RETRY_AFTER_S)
        result = embedder.embed_documents_sync(batch)  # one retry; a second failure propagates
    return [list(v) for v in result.embeddings]


def embed_texts(
    embedder: Embedder,
    texts: Sequence[str],
    *,
    dims: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> list[list[float]]:
    """Embed texts as documents, one vector per text, in order. Every vector must have `dims`
    entries (default EMBED_DIMS), the size of the chunks.embedding column."""
    dims = dims or settings.embed_dims
    vectors: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        batch = texts[i : i + BATCH]
        got = _embed_batch(embedder, batch, sleep)
        if len(got) != len(batch) or any(len(v) != dims for v in got):
            raise ValueError(
                f"expected {len(batch)} vectors of {dims} dims (EMBED_DIMS) from the model"
            )
        vectors.extend(got)
    return vectors
