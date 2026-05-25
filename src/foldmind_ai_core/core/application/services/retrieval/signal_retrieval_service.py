from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.embedding_results import embed_one
from foldmind_ai_core.core.application.execution.blocking_io import run_blocking
from foldmind_ai_core.core.application.ports.outbound.provider.embedding import (
    EmbeddingProvider,
)
from foldmind_ai_core.core.application.ports.outbound.store.vector_store import SignalVectorStore
from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.models.retrieval import SignalRetrievalResult


@dataclass(slots=True)
class SignalRetrievalService:
    embeddings: EmbeddingProvider
    signal_vectors: SignalVectorStore

    async def search(
        self,
        query: RetrievalQuery,
        *,
        signal_type: str | None = None,
        top_k: int = 20,
    ) -> list[SignalRetrievalResult]:
        query_vector = await run_blocking(embed_one, self.embeddings, query.text)
        return await run_blocking(
            self.signal_vectors.search_signals,
            tenant=query.request_context.tenant,
            query_vector=query_vector,
            top_k=top_k,
            signal_type=signal_type,
            scope=query.scope,
        )
