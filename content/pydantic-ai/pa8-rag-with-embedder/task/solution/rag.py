"""Task: a tiny RAG index in pure Python (chunk, embed, rank by cosine)."""

import math

from pydantic_ai import Embedder

Index = list[tuple[str, list[float]]]


def chunk(text: str) -> list[str]:
    """Split Markdown `text` into one chunk per `## ` section, never inside a code fence."""
    parts: list[list[str]] = [[]]  # parts[0] holds any text before the first `## ` heading
    fence = ""  # the marker (``` or ~~~) of the fence we are inside, or "" outside a fence
    for line in text.splitlines():
        marker = line.lstrip()[:3]
        if marker in ("```", "~~~"):
            if not fence:
                fence = marker  # a fence opens
            elif marker == fence:
                fence = ""  # the same marker closes it
        elif line.startswith("## ") and not fence:
            parts.append([])  # a real heading starts a new chunk
        parts[-1].append(line)
    chunks = ["\n".join(lines).strip() for lines in parts]
    return [c for c in chunks if c]


async def index(chunks: list[str], embedder: Embedder) -> Index:
    """Embed every chunk as a document and return (chunk, vector) pairs, in order."""
    if not chunks:
        return []  # do not call a model with nothing to embed
    result = await embedder.embed_documents(chunks)
    return [(text, list(vector)) for text, vector in zip(chunks, result.embeddings, strict=True)]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0  # a zero vector has no direction: score 0, not a crash


async def search(query: str, index: Index, embedder: Embedder, k: int = 3) -> list[str]:
    """Return the `k` chunks whose vectors are most similar (by cosine) to the query."""
    result = await embedder.embed_query(query)
    q = result.embeddings[0]
    scored = [(_cosine(q, vector), text) for text, vector in index]
    # Python's sort is stable, so chunks with equal scores keep their original order.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [text for _, text in scored[: max(k, 0)]]
