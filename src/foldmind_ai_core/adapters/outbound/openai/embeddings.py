from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.openai.client import (
    OpenAIClient,
    field_value,
)
from foldmind_ai_core.adapters.outbound.openai.errors import AIProviderError
from foldmind_ai_core.shared.types import Vector
from foldmind_ai_core.shared.validation import InvalidInputError, require_non_blank


@dataclass(slots=True)
class OpenAIEmbeddingProvider:
    model: str
    client: OpenAIClient
    dimensions: int | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.model, "model")
        if self.dimensions is not None and self.dimensions <= 0:
            raise InvalidInputError("dimensions must be greater than zero.")

    def embed_texts(self, texts: list[str]) -> list[Vector]:
        if not texts:
            raise InvalidInputError("texts must not be empty.")
        for index, text in enumerate(texts):
            require_non_blank(text, f"texts[{index}]")

        try:
            response = self.client.create_embeddings(_embedding_request(self, texts))
        except Exception as exc:
            raise AIProviderError("OpenAI embedding generation failed.") from exc

        return _vectors_from_response(response, expected_count=len(texts))


def _embedding_request(
    provider: OpenAIEmbeddingProvider,
    texts: list[str],
) -> dict[str, object]:
    request: dict[str, object] = {
        "model": provider.model,
        "input": texts,
        "encoding_format": "float",
    }
    if provider.dimensions is not None:
        request["dimensions"] = provider.dimensions
    return request


def _vectors_from_response(response: object, *, expected_count: int) -> list[Vector]:
    data_value = field_value(response, "data")
    if not isinstance(data_value, list):
        raise AIProviderError("OpenAI embedding response did not include data.")
    data = list(data_value)
    if len(data) != expected_count:
        raise AIProviderError(
            f"OpenAI returned {len(data)} embeddings for {expected_count} input texts."
        )

    ordered = sorted(data, key=lambda item: int(field_value(item, "index")))
    vectors: list[Vector] = []
    for index, item in enumerate(ordered):
        if int(field_value(item, "index")) != index:
            raise AIProviderError("OpenAI embedding indexes did not match input order.")
        embedding = field_value(item, "embedding")
        if not isinstance(embedding, list):
            raise AIProviderError("OpenAI embedding item did not include a vector.")
        vectors.append([float(value) for value in embedding])
    return vectors
