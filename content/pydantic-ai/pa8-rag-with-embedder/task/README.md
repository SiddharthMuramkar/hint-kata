# Task: a tiny RAG index in plain Python

You will build the smallest version of the pipeline from the lesson. It cuts a Markdown page into chunks, turns the chunks into vectors, and finds the chunks closest to a question. There is no database and no numpy. The cosine maths is yours.

Open `rag.py` in your workspace. It has three TODO comments.

1. **`chunk(text)`**: return a list of chunks, one per `## ` section.
   - A line that starts with `## ` (two hashes and a space) starts a new chunk. A line that starts with `# ` or `### ` does not.
   - A chunk is its heading line plus everything up to the next `## ` heading. Strip the ends. Text before the first `## ` heading is a chunk of its own. Leave out empty chunks.
   - Never split inside a code fence. A fence opens on a line that starts with three backticks or three tildes, and it closes on the next line that starts with the same three characters. A `## ` line inside a fence is code, so it must not start a chunk. Read the lesson section "Chunking by headings".
2. **`index(chunks, embedder)`**: return a list of `(chunk, vector)` pairs, in the same order as the chunks.
   - Use `await embedder.embed_documents(chunks)`, once, for all the chunks.
   - If there are no chunks, return `[]` and do not call the model.
3. **`search(query, index, embedder, k)`**: return the text of the `k` chunks closest to the query, best first.
   - Embed the question with `await embedder.embed_query(query)`.
   - Rank by cosine similarity, `dot(a, b) / (|a| * |b|)`, written in plain Python. A vector of all zeros has no direction: score it `0.0` and do not divide by zero.
   - Chunks with the same score keep the order they have in `index`.

Both `index` and `search` are `async def`, so do not use `asyncio.run` inside them.

## How the check works

The hidden tests need no API key and no network. They set `ALLOW_MODEL_REQUESTS = False` and use a small subclass of `TestEmbeddingModel`. The stock `TestEmbeddingModel` gives every text the same vector, so the subclass swaps in vectors that count how often the words `cats`, `money` and `code` appear. That way the tests know the right ranking before they run. The subclass also records each call, so a test can see whether you used `embed_documents` or `embed_query`. The tests check that:

- `chunk` cuts at `## ` headings only, keeps the text before the first one, and never cuts inside a fence (both kinds).
- `index` pairs each chunk with its own vector, makes one `embed_documents` call, and makes no call for an empty list.
- `search` embeds the question as a query and ranks by cosine, not by the raw dot product.
- Equal scores keep the index order. With the stock `TestEmbeddingModel`, every score is equal.
- A zero vector, for a chunk or for the question, does not crash the search.
- `k` bigger than the index, and `k` of zero, both work.
- Your code imports neither numpy nor anything from `app`.

Press **Check my work** when you are ready. If a test fails, read its message and the lesson sections "Testing without a network", "Chunking by headings" and "Storing vectors in Postgres".
