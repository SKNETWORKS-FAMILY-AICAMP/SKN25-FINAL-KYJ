from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.core.application.ports.outbound.graph_store import GraphStore
from foldmind_ai_core.core.application.ports.outbound.vector_store import (
    DocumentChunkVectorStore,
    DocumentVectorStore,
)
from foldmind_ai_core.core.application.services.document_retrieval_policy import (
    DocumentRetrievalConfig,
    boost_chunk_results,
    candidate_scope,
    dedupe_results_by_document,
    rank_document_candidates,
)
from foldmind_ai_core.core.application.services.embedding_results import embed_one
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.queries.scope_matching import (
    sort_by_timestamp_scope,
)
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult


@dataclass(slots=True)
class DocumentRetrievalService:
    embeddings: EmbeddingProvider
    chunk_vectors: DocumentChunkVectorStore
    document_vectors: DocumentVectorStore
    graph: GraphStore
    config: DocumentRetrievalConfig = field(default_factory=DocumentRetrievalConfig)

    def search(
        self,
        *,
        tenant: str,
        query: RetrievalQuery,
        comprehensive: bool = False,
    ) -> list[RetrievalResult]:
        query_vector = embed_one(self.embeddings, query.text)
        document_results = self.document_vectors.search_documents(
            tenant=tenant,
            query_vector=query_vector,
            top_k=self.config.document_top_k,
            scope=query.scope,
        )
        graph_results = self.graph.graph_search(
            tenant=tenant,
            query_text=query.text,
            top_k=self.config.graph_top_k,
            scope=query.scope,
        )
        document_candidates = rank_document_candidates(
            document_results=document_results,
            graph_results=graph_results,
            both_sources_bonus=self.config.both_sources_bonus,
        )
        scoped_candidates = candidate_scope(query.scope, document_candidates)
        results = self.chunk_vectors.search_chunks(
            tenant=tenant,
            query_vector=query_vector,
            top_k=(
                self.config.comprehensive_top_k if comprehensive else self.config.top_k
            ),
            scope=scoped_candidates,
        )
        boosted_results = boost_chunk_results(results, document_candidates)
        boosted_results = sort_by_timestamp_scope(
            boosted_results,
            scope=query.scope,
            timestamp_value=lambda result, field: getattr(result.chunk, field),
        )
        if comprehensive:
            return dedupe_results_by_document(boosted_results)
        return boosted_results
