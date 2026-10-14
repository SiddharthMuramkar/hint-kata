"""Unit tests for app/ingest/embed.py. Only TestEmbeddingModel: nothing calls the network."""

from collections.abc import Sequence

import pytest
from pydantic_ai import Embedder, models
from pydantic_ai.embeddings import EmbeddingResult, EmbeddingSettings, TestEmbeddingModel
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.embeddings.result import EmbedInputType
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError

from app.config import Settings, settings
from app.ingest.embed import BATCH, RETRY_AFTER_S, embed_texts, make_embedder


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)


class Recorder(TestEmbeddingModel):
    """Records batch sizes, answers with [len(text), 0, 0, 0], and can fail the first calls."""

    def __init__(self, failures: Sequence[ModelAPIError] = ()) -> None:
        super().__init__(dimensions=4)
        self.batches: list[int] = []
        self.failures = list(failures)

    async def embed(
        self,
        inputs: str | Sequence[str],
        *,
        input_type: EmbedInputType,
        settings: EmbeddingSettings | None = None,
    ) -> EmbeddingResult:
        texts = [inputs] if isinstance(inputs, str) else list(inputs)
        self.batches.append(len(texts))
        if self.failures:
            raise self.failures.pop(0)
        result = await super().embed(texts, input_type=input_type, settings=settings)
        result.embeddings = [[float(len(t)), 0.0, 0.0, 0.0] for t in texts]
        return result


def http(status: int) -> ModelHTTPError:
    return ModelHTTPError(status_code=status, model_name="m", body=None)


def test_inputs_go_out_in_batches_of_at_most_64_and_keep_their_order() -> None:
    model = Recorder()
    texts = ["x" * i for i in range(1, 151)]
    vectors = embed_texts(Embedder(model), texts, dims=4)
    assert model.batches == [BATCH, BATCH, 150 - 2 * BATCH]
    assert BATCH == 64
    assert [v[0] for v in vectors] == [float(i) for i in range(1, 151)]


def test_no_texts_means_no_requests() -> None:
    model = Recorder()
    assert embed_texts(Embedder(model), [], dims=4) == []
    assert model.batches == []


@pytest.mark.parametrize(
    "failure", [http(429), http(503), ModelAPIError("m", "connection dropped")]
)
def test_a_transient_error_is_retried_once(failure: ModelAPIError) -> None:
    model = Recorder([failure])
    waits: list[float] = []
    vectors = embed_texts(Embedder(model), ["a", "bb"], dims=4, sleep=waits.append)
    assert [v[0] for v in vectors] == [1.0, 2.0]
    assert model.batches == [2, 2] and waits == [RETRY_AFTER_S]


def test_a_second_failure_is_raised() -> None:
    model = Recorder([http(503), http(503)])
    with pytest.raises(ModelHTTPError):
        embed_texts(Embedder(model), ["a"], dims=4, sleep=lambda _: None)
    assert model.batches == [1, 1]


def test_a_permanent_error_is_not_retried() -> None:
    model = Recorder([http(401)])
    with pytest.raises(ModelHTTPError):
        embed_texts(Embedder(model), ["a"], dims=4, sleep=lambda _: pytest.fail("slept"))
    assert model.batches == [1]


def test_the_vector_size_must_match_embed_dims() -> None:
    with pytest.raises(ValueError, match="EMBED_DIMS"):
        embed_texts(Embedder(Recorder()), ["a"], dims=8)


def test_default_dims_come_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    assert settings.embed_dims == 1536 and "text-embedding-3-small" in settings.embed_model
    embedder = Embedder(TestEmbeddingModel(dimensions=settings.embed_dims))
    assert [len(v) for v in embed_texts(embedder, ["a", "b"])] == [1536, 1536]
    monkeypatch.setattr(settings, "embed_dims", 8)
    with pytest.raises(ValueError, match="EMBED_DIMS"):
        embed_texts(embedder, ["a"])


def test_empty_env_lines_fall_back_to_the_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("EMBED_DIMS", "EMBED_MODEL", "OPENROUTER_ZDR"):
        monkeypatch.setenv(name, "")  # a line like `EMBED_DIMS=` in the local env file
    fresh = Settings(_env_file=None)
    assert (
        fresh.embed_dims == 1536
        and fresh.embed_model == Settings.model_fields["embed_model"].default
    )
    assert fresh.openrouter_zdr is False


def test_make_embedder_builds_an_openrouter_model_and_tests_cannot_reach_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openrouter_api_key", "test-key-not-real")
    embedder = make_embedder("openrouter:openai/text-embedding-3-small")
    assert isinstance(embedder.model, OpenAIEmbeddingModel)
    assert embedder.model.model_name == "openai/text-embedding-3-small"
    assert embedder.model.system == "openrouter"
    with pytest.raises(RuntimeError, match="ALLOW_MODEL_REQUESTS"):
        embed_texts(embedder, ["hello"])
