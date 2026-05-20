from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.factories.retrieval_results import (
    search_signals_result_from_domain,
)
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.results.retrieval import SearchSignalsResult
from foldmind_ai_core.core.application.services.signal_retrieval_service import (
    SignalRetrievalService,
)


@dataclass(slots=True)
class FindSignalsUseCase:
    retrieval: SignalRetrievalService

    def execute(
        self,
        query: RetrievalQuery,
        *,
        signal_type: str | None = None,
        top_k: int = 20,
    ) -> SearchSignalsResult:
        return search_signals_result_from_domain(
            self.retrieval.search(
                query,
                signal_type=signal_type,
                top_k=top_k,
            )
        )
