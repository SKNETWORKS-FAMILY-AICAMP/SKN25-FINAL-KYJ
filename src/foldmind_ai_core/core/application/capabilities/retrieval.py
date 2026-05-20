from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.commands.recommendation import RecommendFolderCommand
from foldmind_ai_core.core.application.queries.retrieval import FolderSearchQuery, RetrievalQuery
from foldmind_ai_core.core.application.results.retrieval import (
    RecommendFolderResult,
    SearchDocumentsResult,
    SearchFoldersResult,
    SearchSignalsResult,
)
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult


class DocumentSearchCapability(Protocol):
    def execute(
        self,
        query: RetrievalQuery,
        *,
        require_comprehensive_search: bool = False,
    ) -> SearchDocumentsResult:
        ...


class FolderSearchCapability(Protocol):
    def execute(
        self,
        query: FolderSearchQuery,
    ) -> SearchFoldersResult:
        ...


class SignalSearchCapability(Protocol):
    def execute(
        self,
        query: RetrievalQuery,
        *,
        signal_type: str | None = None,
        top_k: int = 20,
    ) -> SearchSignalsResult:
        ...


class FolderRecommendationCapability(Protocol):
    def execute(self, command: RecommendFolderCommand) -> RecommendFolderResult:
        ...


class RetrievalResultFilter(Protocol):
    def filter(
        self,
        *,
        query: RetrievalQuery,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        ...
