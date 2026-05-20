from __future__ import annotations

import math
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
        if self.dimensions is not None and (
            isinstance(self.dimensions, bool)
            or not isinstance(self.dimensions, int)
            or self.dimensions <= 0
        ):
            raise InvalidInputError("dimensions must be a positive integer.")

    def embed_texts(self, texts: list[str]) -> list[Vector]:
        if not texts:
            raise InvalidInputError("texts must not be empty.")
        for index, text in enumerate(texts):
            require_non_blank(text, f"texts[{index}]")

        request: dict[str, object] = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
        }
        if self.dimensions is not None:
            request["dimensions"] = self.dimensions
        try:
            response = self.client.create_embeddings(request)
        except Exception as exc:
            raise AIProviderError("OpenAI embedding generation failed.") from exc

        try:
            return _vectors_from_response(response, expected_count=len(texts))
        except AIProviderError:
            raise
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise AIProviderError("OpenAI embedding response was malformed.") from exc


def _vectors_from_response(response: object, *, expected_count: int) -> list[Vector]:
    data_value = field_value(response, "data")
    if not isinstance(data_value, list):
        raise AIProviderError("OpenAI embedding response did not include data.")
    data = list(data_value)
    if len(data) != expected_count:
        raise AIProviderError(
            f"OpenAI returned {len(data)} embeddings for {expected_count} input texts."
        )

    indexed_data = [(_embedding_index(item), item) for item in data]
    indexed_data.sort(key=lambda item: item[0])
    vectors: list[Vector] = []
    for index, (item_index, item) in enumerate(indexed_data):
        if item_index != index:
            raise AIProviderError("OpenAI embedding positions did not match input order.")
        embedding = field_value(item, "embedding")
        if not isinstance(embedding, list):
            raise AIProviderError("OpenAI embedding item did not include a vector.")
        vectors.append(_vector_from_embedding(embedding))
    return vectors


def _embedding_index(item: object) -> int:
    value = field_value(item, "index")
    if isinstance(value, bool) or not isinstance(value, int):
        raise AIProviderError("OpenAI embedding index must be an integer.")
    return value


def _vector_from_embedding(embedding: list[object]) -> Vector:
    vector: Vector = []
    for value in embedding:
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise AIProviderError("OpenAI embedding vector must contain numbers.")
        coordinate = float(value)
        if not math.isfinite(coordinate):
            raise AIProviderError("OpenAI embedding vector must contain finite numbers.")
        vector.append(coordinate)
    return vector
