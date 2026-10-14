"""Task: a tiny RAG index in pure Python (chunk, embed, rank by cosine). No numpy."""

from pydantic_ai import Embedder

Index = list[tuple[str, list[float]]]  # (chunk text, its vector)


def chunk(text: str) -> list[str]:
    """Split Markdown `text` into one chunk per `## ` section, never inside a code fence."""
    # TODO 1: split `text` into chunks.
    #   - A chunk starts at a line that begins with "## " (two hashes and a space).
    #     Lines that begin with "# " or "### " do not start a new chunk.
    #   - A chunk is its heading line plus everything up to the next heading. Strip the ends.
    #   - Text before the first "## " heading is its own chunk. Drop chunks that are empty.
    #   - A "## " line inside a fenced code block is code, not a heading. A fence opens on a
    #     line that starts with ``` or ~~~ and closes on the next line that starts with the
    #     same three characters. Track whether you are inside one as you read line by line.
    return []


async def index(chunks: list[str], embedder: Embedder) -> Index:
    """Embed every chunk as a document and return (chunk, vector) pairs, in order."""
    # TODO 2: embed the chunks.
    #   - Use `await embedder.embed_documents(chunks)`: these are documents you will search.
    #   - One call for all the chunks, not one call per chunk.
    #   - `result.embeddings` holds one vector per chunk, in the same order. Pair each chunk
    #     with its vector, and return plain lists of floats.
    #   - If there are no chunks, return [] and do not call the model at all.
    return []


async def search(query: str, index: Index, embedder: Embedder, k: int = 3) -> list[str]:
    """Return the `k` chunks whose vectors are most similar (by cosine) to the query."""
    # TODO 3: rank the chunks.
    #   - Embed the question with `await embedder.embed_query(query)`: a query, not a document.
    #     The vector is `result.embeddings[0]`.
    #   - Cosine similarity is dot(a, b) / (|a| * |b|). Write it in plain Python with `math`.
    #     Do not import numpy.
    #   - A vector of all zeros has no direction. Give it a score of 0.0 and do not crash.
    #   - Return the text of the best `k` chunks, best first. If two chunks have the same
    #     score, keep the order they have in `index`.
    return []
