from __future__ import annotations

from typing import Protocol

from ai_core.common.types import Vector


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        """Return a vector for each input text."""
