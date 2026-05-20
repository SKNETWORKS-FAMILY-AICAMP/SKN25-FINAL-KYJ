from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult


class DocumentKeywordSearchStore(Protocol):
    def search_chunks(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        """Return top-k chunk-level keyword matches."""
        ...
