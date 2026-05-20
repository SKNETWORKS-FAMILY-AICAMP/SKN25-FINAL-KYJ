from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.core.application.ports.outbound.vector_store import SignalVectorStore
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.services.embedding_results import embed_one
from foldmind_ai_core.core.domain.models.retrieval.results import SignalRetrievalResult


@dataclass(slots=True)
class SignalRetrievalService:
    embeddings: EmbeddingProvider
    signal_vectors: SignalVectorStore

    def search(
        self,
        query: RetrievalQuery,
        *,
        signal_type: str | None = None,
        top_k: int = 20,
    ) -> list[SignalRetrievalResult]:
        query_vector = embed_one(self.embeddings, query.text)
        return self.signal_vectors.search_signals(
            tenant=query.request_context.tenant,
            query_vector=query_vector,
            top_k=top_k,
            signal_type=signal_type,
            scope=query.scope,
        )
