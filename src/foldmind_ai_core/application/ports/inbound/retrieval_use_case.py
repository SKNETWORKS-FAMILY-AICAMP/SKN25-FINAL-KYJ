from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.domain.generation.results import GeneratedTextResult
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.retrieval.results import RetrievalResult


class FindDocumentsUseCasePort(Protocol):
    def execute(
        self,
        query: AIQuery,
        *,
        require_comprehensive_search: bool = False,
    ) -> list[RetrievalResult]:
        ...


class SearchDocumentsUseCasePort(Protocol):
    def execute(self, query: AIQuery) -> list[RetrievalResult]:
        ...


class AnswerQuestionUseCasePort(Protocol):
    def execute(self, query: AIQuery) -> GeneratedTextResult:
        ...
