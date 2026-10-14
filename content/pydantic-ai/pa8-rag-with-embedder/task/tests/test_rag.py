import ast
import asyncio
import dataclasses
from collections.abc import Sequence
from pathlib import Path

import rag
from pydantic_ai import Embedder, models
from pydantic_ai.embeddings import EmbeddingResult, EmbeddingSettings, TestEmbeddingModel
from pydantic_ai.embeddings.result import EmbedInputType
from rag import chunk, index, search

models.ALLOW_MODEL_REQUESTS = False  # no test here may reach a real model

AXES = ("cats", "money", "code")  # a vector counts how often each word appears in the text


class CountingModel(TestEmbeddingModel):
    """TestEmbeddingModel returns [1.0] * 8 for every text, so every cosine would tie.

    This subclass keeps its result type, settings tracking and token usage, but replaces the
    vectors with word counts, so a test can know the right ranking in advance. It also records
    each call, so a test can check which method (query or document) the code used.
    """

    __test__ = False

    def __init__(self) -> None:
        super().__init__(dimensions=len(AXES))
        self.calls: list[tuple[str, list[str]]] = []

    async def embed(
        self,
        inputs: str | Sequence[str],
        *,
        input_type: EmbedInputType,
        settings: EmbeddingSettings | None = None,
    ) -> EmbeddingResult:
        result = await super().embed(inputs, input_type=input_type, settings=settings)
        self.calls.append((input_type, list(result.inputs)))
        vectors = [[float(t.lower().count(word)) for word in AXES] for t in result.inputs]
        return dataclasses.replace(result, embeddings=vectors)


def make() -> tuple[CountingModel, Embedder]:
    model = CountingModel()
    return model, Embedder(model)


DOC = """# Pets and money

Intro text before any section.

## Cats

Cats sleep a lot.

### Kittens

Kittens are small cats.

## Money

Money buys cat food.
"""

FENCED = """## Setup

Run this:

```bash
## not a heading, this is a shell comment
pip install thing
```

## Usage

~~~python
## also not a heading
print("hi")
~~~

Done.
"""


def test_chunk_splits_on_level_two_headings() -> None:
    got = chunk(DOC)
    assert len(got) == 3, "expected the text before the first heading plus two sections"
    assert got[0].startswith("# Pets and money") and "Intro text" in got[0]
    assert (
        got[1].startswith("## Cats") and "### Kittens" in got[1] and "Kittens are small" in got[1]
    )
    assert got[2] == "## Money\n\nMoney buys cat food."
    assert got == [c.strip() for c in got], "strip the ends of every chunk"


def test_chunk_keeps_one_section_whole() -> None:
    got = chunk("## A\n\nfirst\n\nsecond\n\n## B\n\nthird\n")
    assert got == ["## A\n\nfirst\n\nsecond", "## B\n\nthird"]


def test_chunk_never_splits_inside_a_code_fence() -> None:
    got = chunk(FENCED)
    assert len(got) == 2, f"a '## ' line inside a fence is code, not a heading. Got {got!r}"
    assert "## not a heading" in got[0] and "pip install thing" in got[0]
    assert got[1].startswith("## Usage") and "## also not a heading" in got[1]
    assert got[1].rstrip().endswith("Done.")


def test_chunk_of_empty_text_is_empty() -> None:
    assert chunk("") == []
    assert chunk("   \n\n  ") == []


def test_index_pairs_each_chunk_with_its_vector_using_embed_documents() -> None:
    model, embedder = make()
    chunks = ["Cats purr.", "Money talks.", "Code runs."]
    got = asyncio.run(index(chunks, embedder))
    assert got == [
        ("Cats purr.", [1.0, 0.0, 0.0]),
        ("Money talks.", [0.0, 1.0, 0.0]),
        ("Code runs.", [0.0, 0.0, 1.0]),
    ]
    assert model.calls == [("document", chunks)], (
        "embed all the chunks in one embed_documents call, not one call per chunk"
    )
    assert all(isinstance(v, list) for _, v in got), "return plain lists of floats"


def test_index_of_no_chunks_does_not_call_the_model() -> None:
    model, embedder = make()
    assert asyncio.run(index([], embedder)) == []
    assert model.calls == []


def test_index_works_with_the_stock_test_model() -> None:
    embedder = Embedder(TestEmbeddingModel())
    got = asyncio.run(index(["a", "b"], embedder))
    assert got == [("a", [1.0] * 8), ("b", [1.0] * 8)]


def run_search(texts: list[str], query: str, k: int) -> list[str]:
    _, embedder = make()

    async def go() -> list[str]:
        idx = await index(texts, embedder)
        return await search(query, idx, embedder, k)

    return asyncio.run(go())


def test_search_returns_the_closest_chunks_best_first() -> None:
    texts = [
        "All about money.",
        "Cats, cats and more cats.",
        "How to write code.",
        "Cats and money.",
    ]
    got = run_search(texts, "cats", 2)
    assert got == ["Cats, cats and more cats.", "Cats and money."]


def test_search_embeds_the_question_as_a_query() -> None:
    model, embedder = make()
    idx = asyncio.run(index(["Cats purr."], embedder))
    asyncio.run(search("cats?", idx, embedder, 1))
    assert model.calls[-1] == ("query", ["cats?"]), "use embed_query for the question"


def test_search_ranks_by_cosine_not_by_dot_product() -> None:
    # Query vector [1, 1, 0]. The long text has the bigger dot product (7 against 2),
    # but the short one points the same way as the query, so its cosine is 1.0.
    long_text = "cats " * 6 + "money"
    short_text = "cats money"
    got = run_search([long_text, short_text], "cats money", 1)
    assert got == [short_text], "rank by cosine similarity: divide the dot product by both lengths"


def test_search_with_equal_scores_keeps_the_index_order() -> None:
    embedder = Embedder(TestEmbeddingModel())  # every vector is [1.0] * 8: every score ties
    texts = ["first", "second", "third", "fourth"]

    async def go() -> list[str]:
        idx = await index(texts, embedder)
        return await search("anything", idx, embedder, 3)

    assert asyncio.run(go()) == ["first", "second", "third"]


def test_search_survives_a_zero_vector() -> None:
    # "nothing" has no counted word, so its vector is [0, 0, 0]. "zzz" does the same for the query.
    got = run_search(["nothing", "Cats purr."], "cats", 2)
    assert got == ["Cats purr.", "nothing"], "a zero vector scores 0.0 and ranks last"
    got = run_search(["one", "two"], "zzz", 2)
    assert got == ["one", "two"], "a zero query vector must not crash"


def test_search_k_bigger_than_the_index_and_k_zero() -> None:
    got = run_search(["Cats purr.", "Money talks."], "cats", 10)
    assert got == ["Cats purr.", "Money talks."]
    got = run_search(["Cats purr."], "cats", 0)
    assert got == []


def test_the_code_uses_no_numpy_and_no_app_imports() -> None:
    tree = ast.parse(Path(rag.__file__).read_text())
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    assert not [n for n in names if n.split(".")[0] in {"numpy", "app"}], names
