"""The runtime claims lesson PA8 makes about Pydantic AI 2.56.0 and pgvector, run for real.

No network and no Postgres: everything goes through TestEmbeddingModel or a stand-in model.
If a Pydantic AI upgrade changes one of these behaviours, the lesson text needs a second look.
"""

import asyncio
import dataclasses
from collections.abc import Sequence

import pytest
from pgvector import Vector
from pydantic_ai import Embedder, models
from pydantic_ai.embeddings import EmbeddingResult, EmbeddingSettings, TestEmbeddingModel
from pydantic_ai.embeddings.result import EmbedInputType


class Recorder(TestEmbeddingModel):
    """TestEmbeddingModel that remembers every call it gets."""

    __test__ = False

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, int]] = []

    async def embed(
        self,
        inputs: str | Sequence[str],
        *,
        input_type: EmbedInputType,
        settings: EmbeddingSettings | None = None,
    ) -> EmbeddingResult:
        result = await super().embed(inputs, input_type=input_type, settings=settings)
        self.calls.append((input_type, len(result.inputs)))
        return result


def test_test_model_gives_every_text_the_same_eight_ones() -> None:
    embedder = Embedder(TestEmbeddingModel())

    async def go() -> None:
        q = await embedder.embed_query("cats")
        d = await embedder.embed_documents(["cats", "a completely different text"])
        assert q.embeddings == [[1.0] * 8]
        assert d.embeddings == [[1.0] * 8, [1.0] * 8]

    asyncio.run(go())


def test_test_model_dimensions_come_from_the_constructor_or_the_settings() -> None:
    async def go() -> None:
        assert len((await Embedder(TestEmbeddingModel(dimensions=3)).embed_query("q"))[0]) == 3
        model = TestEmbeddingModel()
        result = await Embedder(model).embed_query("q", settings=EmbeddingSettings(dimensions=1536))
        assert len(result[0]) == 1536
        assert model.last_settings == {"dimensions": 1536}

    asyncio.run(go())


def test_the_embedder_sends_the_whole_list_in_one_call_and_names_the_input_type() -> None:
    model = Recorder()
    embedder = Embedder(model)

    async def go() -> None:
        texts = [f"text {i}" for i in range(500)]
        result = await embedder.embed_documents(texts)
        assert len(result.embeddings) == 500
        assert result["text 7"] == result[7]  # a result is indexable by position or by text
        await embedder.embed_query("one question")

    asyncio.run(go())
    assert model.calls == [("document", 500), ("query", 1)]


def test_sync_methods_exist_and_agree() -> None:
    embedder = Embedder(TestEmbeddingModel())
    assert embedder.embed_query_sync("x").embeddings == [[1.0] * 8]
    assert len(embedder.embed_documents_sync(["a", "b", "c"]).embeddings) == 3


def test_a_stand_in_model_can_replace_the_vectors_and_keep_the_result_type() -> None:
    class Words(TestEmbeddingModel):
        __test__ = False

        async def embed(
            self,
            inputs: str | Sequence[str],
            *,
            input_type: EmbedInputType,
            settings: EmbeddingSettings | None = None,
        ) -> EmbeddingResult:
            result = await super().embed(inputs, input_type=input_type, settings=settings)
            return dataclasses.replace(result, embeddings=[[float(len(t))] for t in result.inputs])

    result = asyncio.run(Embedder(Words()).embed_documents(["a", "abc"]))
    assert result.embeddings == [[1.0], [3.0]]
    assert result.model_name == "test"


def test_allow_model_requests_false_blocks_a_real_embedder_but_not_the_test_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("tiktoken")  # the OpenAI embedding model needs it; the ingestion PR adds it
    monkeypatch.setenv("OPENROUTER_API_KEY", "unused-placeholder")
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    embedder = Embedder("openrouter:openai/text-embedding-3-small")
    with pytest.raises(RuntimeError, match="ALLOW_MODEL_REQUESTS"):
        asyncio.run(embedder.embed_query("hello"))
    with pytest.raises(RuntimeError, match="ALLOW_MODEL_REQUESTS"):
        asyncio.run(embedder.embed_documents(["hello"]))
    with embedder.override(model=TestEmbeddingModel()):
        assert asyncio.run(embedder.embed_query("hello")).embeddings == [[1.0] * 8]


def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Reciprocal rank fusion, the same code as in the lesson."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            scores[doc] = scores.get(doc, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def test_rrf_rewards_a_chunk_that_both_lists_like() -> None:
    meaning = ["A", "B", "C"]
    keywords = ["B", "D", "A"]
    fused = rrf([meaning, keywords])
    assert [doc for doc, _ in fused] == ["B", "A", "D", "C"]
    scores = dict(fused)
    assert round(scores["A"], 6) == round(1 / 61 + 1 / 63, 6) == 0.032266
    assert round(scores["B"], 6) == round(1 / 62 + 1 / 61, 6) == 0.032522
    assert scores["C"] == 1 / 63 and scores["D"] == 1 / 62
    # A chunk only one list found still shows up, below chunks both lists found.
    assert scores["C"] < scores["A"]


def test_pgvector_vector_wraps_a_python_list() -> None:
    assert Vector([1, 2.5, 3]).to_text() == "[1.0,2.5,3.0]"
    assert Vector([1, 2.5, 3]).to_list() == [1.0, 2.5, 3.0]


def test_cosine_and_l2_agree_for_vectors_of_length_one() -> None:
    import math

    def unit(v: list[float]) -> list[float]:
        n = math.sqrt(sum(x * x for x in v))
        return [x / n for x in v]

    q = unit([1.0, 2.0, 3.0])
    docs = [unit([3.0, 2.0, 1.0]), unit([1.0, 2.0, 2.5]), unit([-1.0, 0.0, 1.0])]
    by_cosine = sorted(range(3), key=lambda i: -sum(a * b for a, b in zip(q, docs[i], strict=True)))
    by_l2 = sorted(range(3), key=lambda i: math.dist(q, docs[i]))
    assert by_cosine == by_l2
