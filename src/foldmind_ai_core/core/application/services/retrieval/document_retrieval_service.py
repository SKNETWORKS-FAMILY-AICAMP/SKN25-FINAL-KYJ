from __future__ import annotations
from dataclasses import dataclass, field

from foldmind_ai_core.core.application.embedding_results import embed_one
from foldmind_ai_core.core.application.execution.blocking_io import run_blocking
from foldmind_ai_core.core.application.ports.outbound.provider.embedding import (
    EmbeddingProvider,
)
from foldmind_ai_core.core.application.ports.outbound.session.retrieval_read_session import (
    RetrievalReadSession,
    RetrievalReadSessionProvider,
)
from foldmind_ai_core.core.application.ports.outbound.store.graph_store import GraphStore
from foldmind_ai_core.core.application.ports.outbound.store.vector_store import (
    DocumentChunkVectorStore,
    DocumentVectorStore,
)
from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.models.search import SearchScope
from foldmind_ai_core.core.application.models.retrieval import (
    DocumentTitleKeywordMatch,
    RetrievalResult,
)
from foldmind_ai_core.core.application.services.retrieval.policy import (
    DocumentRetrievalConfig,
    DocumentRetrievalPolicy,
)
from foldmind_ai_core.core.application.search_scope import (
    sort_by_timestamp_scope,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk

@dataclass(slots=True)
class DocumentRetrievalService:
    embeddings: EmbeddingProvider
    chunk_vectors: DocumentChunkVectorStore
    document_vectors: DocumentVectorStore
    graph: GraphStore
    retrieval_reads: RetrievalReadSessionProvider
    config: DocumentRetrievalConfig = field(default_factory=DocumentRetrievalConfig)

    async def search(
        self,
        *,
        tenant: str,
        query: RetrievalQuery,
        comprehensive: bool = False,
    ) -> list[RetrievalResult]:
        policy = DocumentRetrievalPolicy(self.config)
        query_vector = await run_blocking(embed_one, self.embeddings, query.text)
        document_results = await run_blocking(
            self.document_vectors.search_documents,
            tenant=tenant,
            query_vector=query_vector,
            top_k=self.config.document_top_k,
            scope=query.scope,
        )
        graph_results = await run_blocking(
            self.graph.graph_search,
            tenant=tenant,
            query_text=query.text,
            top_k=self.config.graph_top_k,
            scope=query.scope,
        )
        document_candidates = policy.rank_document_candidates(
            document_results=document_results,
            graph_results=graph_results,
        )
        scoped_candidates = policy.candidate_scope(query.scope, document_candidates)
        dense_results = await run_blocking(
            self.chunk_vectors.search_chunks,
            tenant=tenant,
            query_vector=query_vector,
            top_k=(
                self.config.comprehensive_top_k if comprehensive else self.config.top_k
            ),
            scope=scoped_candidates,
        )
        async with self.retrieval_reads.session() as read:
            can_search_keyword, keyword_scope = await _keyword_search_scope(
                read=read,
                tenant=tenant,
                scope=scoped_candidates,
            )
            keyword_results = []
            if can_search_keyword:
                title_source_scores = await read.document_sources.search_titles_by_keyword(
                    tenant=tenant,
                    query_text=query.text.strip(),
                    top_k=self.config.keyword_top_k,
                    document_type=keyword_scope.document_type if keyword_scope else None,
                    document_id=keyword_scope.document_id if keyword_scope else None,
                    document_ids=keyword_scope.document_ids if keyword_scope else (),
                    created_at=keyword_scope.created_at if keyword_scope else None,
                    updated_at=keyword_scope.updated_at if keyword_scope else None,
                    metadata_filter=(
                        keyword_scope.metadata_filter if keyword_scope else None
                    ),
                )
                title_matches = tuple(
                    DocumentTitleKeywordMatch(source=source, score=score)
                    for source, score in title_source_scores
                )
                can_search_chunks, chunk_scope = await _keyword_chunk_scope(
                    read=read,
                    tenant=tenant,
                    scope=keyword_scope,
                )
                chunk_matches: tuple[RetrievalResult, ...] = ()
                if can_search_chunks:
                    chunk_scores = await read.document_projections.search_chunks_by_keyword(
                        tenant=tenant,
                        query_text=query.text.strip(),
                        top_k=self.config.keyword_top_k,
                        document_id=chunk_scope.document_id if chunk_scope else None,
                        document_ids=chunk_scope.document_ids if chunk_scope else (),
                    )
                    chunk_matches = tuple(
                        RetrievalResult(chunk=chunk, score=score)
                        for chunk, score in chunk_scores
                    )
                title_chunks = (
                    await read.document_projections.get_first_chunks_for_documents(
                        tenant=tenant,
                        document_ids=_document_ids_from_title_matches(title_matches),
                        limit=self.config.keyword_top_k,
                    )
                )
                keyword_results = _keyword_results_from_matches(
                    title_matches=title_matches,
                    chunk_matches=chunk_matches,
                    title_chunks=title_chunks,
                    top_k=self.config.keyword_top_k,
                )
        results = policy.merge_hybrid_chunk_results(
            dense_results=dense_results,
            keyword_results=keyword_results,
        )
        boosted_results = policy.boost_chunk_results(results, document_candidates)
        boosted_results = sort_by_timestamp_scope(
            boosted_results,
            scope=query.scope,
            timestamp_value=lambda result, field: getattr(result.chunk, field),
        )
        if comprehensive:
            return policy.dedupe_results_by_document(boosted_results)
        return boosted_results[: self.config.top_k]


async def _keyword_search_scope(
    *,
    read: RetrievalReadSession,
    tenant: str,
    scope: SearchScope | None,
) -> tuple[bool, SearchScope | None]:
    if scope is None or not scope.folder_ids:
        return True, scope

    folder_document_ids = await read.document_relations.document_ids_for_folders(
        tenant=tenant,
        folder_ids=scope.folder_ids,
    )
    if not folder_document_ids:
        return False, None

    folder_document_id_set = set(folder_document_ids)
    if scope.document_id is not None and scope.document_id not in folder_document_id_set:
        return False, None

    document_ids = folder_document_ids
    if scope.document_ids:
        document_ids = tuple(
            document_id
            for document_id in scope.document_ids
            if document_id in folder_document_id_set
        )
        if not document_ids:
            return False, None

    return True, SearchScope(
        document_type=scope.document_type,
        document_id=scope.document_id,
        document_ids=document_ids,
        folder_ids=(),
        created_at=scope.created_at,
        updated_at=scope.updated_at,
        sort=scope.sort,
        metadata_filter=dict(scope.metadata_filter),
    )


async def _keyword_chunk_scope(
    *,
    read: RetrievalReadSession,
    tenant: str,
    scope: SearchScope | None,
) -> tuple[bool, SearchScope | None]:
    if scope is None:
        return True, None
    if not _scope_restricts_source_documents(scope):
        return True, scope

    document_ids = await read.document_sources.document_ids_for_scope(
        tenant=tenant,
        document_type=scope.document_type,
        document_id=scope.document_id,
        document_ids=scope.document_ids,
        created_at=scope.created_at,
        updated_at=scope.updated_at,
        metadata_filter=scope.metadata_filter,
    )
    if not document_ids:
        return False, None

    return True, SearchScope(document_ids=document_ids)


def _scope_restricts_source_documents(scope: SearchScope) -> bool:
    return bool(
        scope.document_type is not None
        or scope.document_id is not None
        or scope.document_ids
        or scope.created_at is not None
        or scope.updated_at is not None
        or scope.metadata_filter
    )


def _keyword_results_from_matches(
    *,
    title_matches: tuple[DocumentTitleKeywordMatch, ...],
    chunk_matches: tuple[RetrievalResult, ...],
    title_chunks: tuple[DocumentChunk, ...],
    top_k: int,
) -> list[RetrievalResult]:
    title_scores = {
        match.source.document_id: match.score for match in title_matches
    }
    merged: dict[str, RetrievalResult] = {}

    for chunk in title_chunks:
        score = title_scores.get(chunk.document_id)
        if score is None:
            continue
        _merge_keyword_result(
            merged=merged,
            result=RetrievalResult(
                chunk=chunk,
                score=score,
            ),
        )

    for match in chunk_matches:
        score = match.score + title_scores.get(match.chunk.document_id, 0.0)
        _merge_keyword_result(
            merged=merged,
            result=RetrievalResult(chunk=match.chunk, score=score),
        )

    results = list(merged.values())
    results.sort(key=lambda result: result.chunk.chunk_id)
    results.sort(key=lambda result: result.chunk.chunk_index)
    results.sort(key=lambda result: result.chunk.updated_at, reverse=True)
    results.sort(key=lambda result: result.score, reverse=True)
    return results[:top_k]


def _merge_keyword_result(
    *,
    merged: dict[str, RetrievalResult],
    result: RetrievalResult,
) -> None:
    existing = merged.get(result.chunk.chunk_id)
    if existing is None or existing.score < result.score:
        merged[result.chunk.chunk_id] = result


def _document_ids_from_title_matches(
    title_matches: tuple[DocumentTitleKeywordMatch, ...],
) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(match.source.document_id for match in title_matches)
    )
