from __future__ import annotations

from typing import Protocol

from ai_core.common.types import Vector
from ai_core.schemas.chunk import DocumentChunk
from ai_core.schemas.query import SearchScope
from ai_core.schemas.retrieval import RetrievalResult


class DocumentVectorStore(Protocol):
    def upsert(self, chunks: list[DocumentChunk], vectors: list[Vector]) -> None:
        """Insert or update vectors for document chunks."""

    def delete(self, *, tenant: str, entity_type: str, entity_id: str) -> None:
        """Delete all vectors for a document."""

    def similarity_search(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        """Return top-k relevant chunks for the query."""
