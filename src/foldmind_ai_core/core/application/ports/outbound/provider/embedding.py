from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.shared.types import Vector


class EmbeddingProvider(Protocol):
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        """Return a vector for each input text."""
        ...
