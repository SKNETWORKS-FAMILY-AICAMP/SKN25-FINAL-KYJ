from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.application.ports.outbound.graph_repository import GraphRepository
from foldmind_ai_core.application.ports.outbound.vector_repository import (
    DocumentChunkVectorRepository,
    DocumentKeywordRepository,
    DocumentVectorRepository,
)
from foldmind_ai_core.application.services.document_retrieval_policy import (
    HybridSearchConfig,
    SearchMode,
    boost_chunk_results,
    candidate_scope,
    dedupe_results_by_document,
    rank_document_candidates,
    reciprocal_rank_fusion,
)
from foldmind_ai_core.domain.retrieval.queries import AIQuery, SearchScope
from foldmind_ai_core.domain.retrieval.results import (
    DocumentRetrievalResult,
    RetrievalResult,
)
from foldmind_ai_core.shared.types import Vector


@dataclass(slots=True)
class DocumentRetrievalService:
    embeddings: EmbeddingProvider
    chunk_vectors: DocumentChunkVectorRepository
    document_vectors: DocumentVectorRepository
    graph: GraphRepository
    keyword_repository: DocumentKeywordRepository | None = None
    config: HybridSearchConfig = field(default_factory=HybridSearchConfig)

    def search(
        self,
        *,
        tenant: str,
        query: AIQuery,
        comprehensive: bool = False,
    ) -> list[RetrievalResult]:
        query_vector = _QueryVector(embeddings=self.embeddings, query=query)
        if comprehensive:
            return self._comprehensive_search(
                tenant=tenant,
                query=query,
                query_vector=query_vector,
            )
        return self._search(
            tenant=tenant,
            query=query,
            query_vector=query_vector,
        )

    def _search(
        self,
        *,
        tenant: str,
        query: AIQuery,
        query_vector: "_QueryVector",
    ) -> list[RetrievalResult]:
        document_candidates = self._document_candidates(
            tenant=tenant,
            query=query,
            query_vector=query_vector,
        )
        scoped_candidates = candidate_scope(query.scope, document_candidates)
        results = self._chunk_results(
            tenant=tenant,
            query=query,
            query_vector=query_vector,
            scope=scoped_candidates,
        )
        return boost_chunk_results(results, document_candidates)

    def _chunk_results(
        self,
        *,
        tenant: str,
        query: AIQuery,
        query_vector: "_QueryVector",
        scope: SearchScope | None,
    ) -> list[RetrievalResult]:
        config = self.config
        keyword_repository = self.keyword_repository
        if config.mode == SearchMode.DENSE or keyword_repository is None:
            return self.chunk_vectors.search_chunks(
                tenant=tenant,
                query_vector=query_vector.get(),
                top_k=config.top_k,
                scope=scope,
            )
        if config.mode == SearchMode.KEYWORD:
            return keyword_repository.search_keywords(
                tenant=tenant,
                query_text=query.text,
                top_k=config.top_k,
                scope=scope,
            )
        dense_results = self.chunk_vectors.search_chunks(
            tenant=tenant,
            query_vector=query_vector.get(),
            top_k=config.dense_top_k,
            scope=scope,
        )
        keyword_results = keyword_repository.search_keywords(
            tenant=tenant,
            query_text=query.text,
            top_k=config.keyword_top_k,
            scope=scope,
        )
        return reciprocal_rank_fusion(
            [dense_results, keyword_results],
            top_k=config.top_k,
            k=config.rrf_k,
        )

    def _comprehensive_search(
        self,
        *,
        tenant: str,
        query: AIQuery,
        query_vector: "_QueryVector",
    ) -> list[RetrievalResult]:
        config = self.config
        document_candidates = self._document_candidates(
            tenant=tenant,
            query=query,
            query_vector=query_vector,
        )
        scoped_candidates = candidate_scope(query.scope, document_candidates)
        dense_results = self.chunk_vectors.search_chunks(
            tenant=tenant,
            query_vector=query_vector.get(),
            top_k=max(config.comprehensive_top_k, config.dense_top_k),
            scope=scoped_candidates,
        )
        result_sets = [dense_results]
        keyword_repository = self.keyword_repository
        if keyword_repository is not None and config.mode != SearchMode.DENSE:
            result_sets.append(
                keyword_repository.search_keywords(
                    tenant=tenant,
                    query_text=query.text,
                    top_k=max(config.comprehensive_top_k, config.keyword_top_k),
                    scope=scoped_candidates,
                )
            )
        fused = reciprocal_rank_fusion(
            result_sets,
            top_k=config.comprehensive_top_k,
            k=config.rrf_k,
        )
        return dedupe_results_by_document(
            boost_chunk_results(fused, document_candidates)
        )

    def _document_candidates(
        self,
        *,
        tenant: str,
        query: AIQuery,
        query_vector: "_QueryVector",
    ) -> list[DocumentRetrievalResult]:
        document_results = self.document_vectors.search_documents(
            tenant=tenant,
            query_vector=query_vector.get(),
            top_k=self.config.document_top_k,
            scope=query.scope,
        )
        graph_results = self.graph.graph_search(
            tenant=tenant,
            query_text=query.text,
            top_k=self.config.graph_top_k,
            scope=query.scope,
        )
        return rank_document_candidates(
            document_results=document_results,
            graph_results=graph_results,
            both_sources_bonus=self.config.both_sources_bonus,
        )


@dataclass(slots=True)
class _QueryVector:
    embeddings: EmbeddingProvider
    query: AIQuery
    value: Vector | None = None

    def get(self) -> Vector:
        if self.value is None:
            self.value = self.embeddings.embed_texts([self.query.text])[0]
        return self.value
