from __future__ import annotations

from typing import Protocol

from ai_core.application.models.queries import SearchScope
from ai_core.application.models.retrieval import RetrievalResult
from ai_core.domain.chunks import DocumentChunk


class DocumentKeywordSearchStore(Protocol):
    def upsert(self, chunks: list[DocumentChunk]) -> None:
        """Insert or update keyword-searchable document chunks."""
        ...

    def delete(self, *, tenant: str, entity_type: str, entity_id: str) -> None:
        """Delete all keyword-searchable chunks for a document."""
        ...

    def keyword_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        """Return top-k keyword/sparse matches for the query."""
        ...
