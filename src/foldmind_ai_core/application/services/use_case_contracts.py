from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.domain.generation.results import FolderRecommendationResult
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.retrieval.results import FolderRetrievalResult, RetrievalResult


class DocumentFinder(Protocol):
    def execute(
        self,
        query: AIQuery,
        *,
        require_comprehensive_search: bool = False,
    ) -> list[RetrievalResult]:
        ...


class RetrievalResultFilter(Protocol):
    def filter(
        self,
        *,
        query: AIQuery,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        ...


class FolderFinder(Protocol):
    def execute(self, request: SourceDocument | AIQuery) -> list[FolderRetrievalResult]:
        ...


class FolderRecommender(Protocol):
    def execute(self, document: SourceDocument) -> FolderRecommendationResult:
        ...
