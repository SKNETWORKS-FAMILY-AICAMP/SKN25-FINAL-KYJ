from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.domain.generation.results import FolderRecommendationResult
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.retrieval.results import FolderRetrievalResult


class FindFoldersUseCasePort(Protocol):
    def execute(self, request: SourceDocument | AIQuery) -> list[FolderRetrievalResult]:
        ...


class RecommendFolderUseCasePort(Protocol):
    def execute(self, document: SourceDocument) -> FolderRecommendationResult:
        ...
