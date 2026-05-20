from __future__ import annotations

from collections.abc import Sequence

from foldmind_ai_core.core.application.errors import ProviderContractError
from foldmind_ai_core.core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.shared.types import Vector


def embed_many(
    embeddings: EmbeddingProvider,
    texts: Sequence[str],
) -> tuple[Vector, ...]:
    vectors = tuple(embeddings.embed_texts(list(texts)))
    if len(vectors) != len(texts):
        raise ProviderContractError(
            "Embedding provider must return one vector per input text."
        )
    return vectors


def embed_one(embeddings: EmbeddingProvider, text: str) -> Vector:
    return embed_many(embeddings, (text,))[0]
