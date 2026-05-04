from __future__ import annotations

from dataclasses import dataclass

from ai_core.agents.search_agent import (
    HybridSearchConfig,
    SearchAgent,
    SearchMode,
    reciprocal_rank_fusion,
)
from ai_core.application.models.queries import AIQuery
from ai_core.application.models.retrieval import RetrievalResult

__all__ = [
    "HybridSearchConfig",
    "HybridSearchUseCase",
    "SearchMode",
    "reciprocal_rank_fusion",
]


@dataclass(slots=True)
class HybridSearchUseCase:
    search: SearchAgent

    def execute(self, query: AIQuery) -> list[RetrievalResult]:
        return self.search.search_documents(query)
