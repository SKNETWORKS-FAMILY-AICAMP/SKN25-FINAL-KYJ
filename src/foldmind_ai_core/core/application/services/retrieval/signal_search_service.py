from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.models.retrieval import (
    RetrievalQuery,
    SignalRetrievalResult,
)
from foldmind_ai_core.core.application.services.retrieval.signal_retrieval_service import (
    SignalRetrievalService,
)


@dataclass(slots=True)
class SignalSearchService:
    retrieval: SignalRetrievalService

    async def search(
        self,
        query: RetrievalQuery,
        *,
        signal_type: str | None = None,
        top_k: int = 20,
    ) -> tuple[SignalRetrievalResult, ...]:
        if not query.text.strip():
            return ()
        return tuple(
            await self.retrieval.search(
                query,
                signal_type=signal_type,
                top_k=top_k,
            )
        )
