from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ai_core.application.models.retrieval import RetrievalResult
from ai_core.application.ports.document_keyword_store import DocumentKeywordSearchStore
from ai_core.application.ports.document_vector_store import DocumentVectorStore
from ai_core.application.ports.embedding import EmbeddingProvider
from ai_core.application.models.queries import AIQuery
from ai_core.common.validation import InvalidInputError


class SearchMode(StrEnum):
    DENSE = "dense"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass(slots=True)
class HybridSearchConfig:
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = 5
    dense_top_k: int = 20
    keyword_top_k: int = 20
    rrf_k: int = 60


def reciprocal_rank_fusion(
    result_sets: list[list[RetrievalResult]],
    *,
    top_k: int,
    k: int,
) -> list[RetrievalResult]:
    scores: dict[str, float] = {}
    results_by_key: dict[str, RetrievalResult] = {}

    for results in result_sets:
        for rank, result in enumerate(results, start=1):
            key = result.chunk.chunk_id
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            results_by_key.setdefault(key, result)

    fused = [
        RetrievalResult(chunk=results_by_key[key].chunk, score=score)
        for key, score in scores.items()
    ]
    fused.sort(key=lambda result: result.score, reverse=True)
    return fused[:top_k]


@dataclass(slots=True)
class HybridSearchUseCase:
    embeddings: EmbeddingProvider
    documents: DocumentVectorStore
    keywords: DocumentKeywordSearchStore
    config: HybridSearchConfig = field(default_factory=HybridSearchConfig)

    def execute(self, query: AIQuery) -> list[RetrievalResult]:
        if query.request_context is None:
            raise InvalidInputError("request_context.tenant is required.")
        tenant = query.request_context.tenant

        if self.config.mode == SearchMode.DENSE:
            return self._dense_search(tenant=tenant, query=query, top_k=self.config.top_k)

        if self.config.mode == SearchMode.KEYWORD:
            return self._keyword_search(tenant=tenant, query=query, top_k=self.config.top_k)

        dense_results = self._dense_search(
            tenant=tenant,
            query=query,
            top_k=self.config.dense_top_k,
        )
        keyword_results = self._keyword_search(
            tenant=tenant,
            query=query,
            top_k=self.config.keyword_top_k,
        )
        return reciprocal_rank_fusion(
            [dense_results, keyword_results],
            top_k=self.config.top_k,
            k=self.config.rrf_k,
        )

    def _dense_search(self, *, tenant: str, query: AIQuery, top_k: int) -> list[RetrievalResult]:
        vector = self.embeddings.embed_texts([query.text])[0]
        return self.documents.similarity_search(
            tenant=tenant,
            query_vector=vector,
            top_k=top_k,
            scope=query.scope,
        )

    def _keyword_search(self, *, tenant: str, query: AIQuery, top_k: int) -> list[RetrievalResult]:
        return self.keywords.keyword_search(
            tenant=tenant,
            query_text=query.text,
            top_k=top_k,
            scope=query.scope,
        )
