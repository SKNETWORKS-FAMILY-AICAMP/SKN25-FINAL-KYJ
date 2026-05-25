from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.embedding_results import embed_one
from foldmind_ai_core.core.application.execution.blocking_io import run_blocking
from foldmind_ai_core.core.application.ports.outbound.provider.embedding import (
    EmbeddingProvider,
)
from foldmind_ai_core.core.application.ports.outbound.session.retrieval_read_session import (
    RetrievalReadSessionProvider,
)
from foldmind_ai_core.core.application.ports.outbound.store.graph_store import GraphStore
from foldmind_ai_core.core.application.ports.outbound.store.vector_store import (
    DocumentChunkVectorStore,
    DocumentVectorStore,
    FolderVectorStore,
)
from foldmind_ai_core.core.application.models.search import SearchScope
from foldmind_ai_core.core.application.services.retrieval.ranking import (
    FolderRetrievalRanker,
)
from foldmind_ai_core.core.application.search_scope import (
    sort_by_timestamp_scope,
)
from foldmind_ai_core.core.application.models.retrieval import FolderRetrievalResult
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class FolderRetrievalService:
    embeddings: EmbeddingProvider
    chunk_vectors: DocumentChunkVectorStore
    document_vectors: DocumentVectorStore
    folder_vectors: FolderVectorStore
    graph: GraphStore
    retrieval_reads: RetrievalReadSessionProvider
    top_k: int = 5
    candidate_multiplier: int = 4

    def __post_init__(self) -> None:
        for field_name in ("top_k", "candidate_multiplier"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise InvalidInputError(f"{field_name} must be a positive integer.")

    async def search(
        self,
        *,
        tenant: str,
        text: str,
        scope: SearchScope | None,
        document_search_scope: SearchScope | None,
        include_document_signals: bool = True,
        excluded_folder_ids: tuple[str, ...] = (),
    ) -> list[FolderRetrievalResult]:
        vector = await run_blocking(embed_one, self.embeddings, text)
        limit = self.top_k * self.candidate_multiplier
        ranker = FolderRetrievalRanker(
            top_k=self.top_k,
            excluded_folder_ids=excluded_folder_ids,
        )

        if include_document_signals:
            document_results = await run_blocking(
                self.document_vectors.search_documents,
                tenant=tenant,
                query_vector=vector,
                top_k=limit,
                scope=document_search_scope,
            )
            for document_result in document_results:
                ranker.add_document_signal(
                    document_id=document_result.document.document_id,
                    score=document_result.score,
                    reason="Similar indexed document belongs to this folder.",
                )

            chunk_results = await run_blocking(
                self.chunk_vectors.search_chunks,
                tenant=tenant,
                query_vector=vector,
                top_k=limit,
                scope=document_search_scope,
            )
            for chunk_result in chunk_results:
                ranker.add_document_signal(
                    document_id=chunk_result.chunk.document_id,
                    score=chunk_result.score,
                    reason="Similar indexed chunk belongs to this folder.",
                )

            graph_results = await run_blocking(
                self.graph.graph_search,
                tenant=tenant,
                query_text=text,
                top_k=limit,
                scope=scope,
            )
            for graph_result in graph_results:
                ranker.add_document_signal(
                    document_id=graph_result.document.document_id,
                    score=graph_result.score,
                    reason="Graph-related document belongs to this folder.",
                )

            document_ids = ranker.document_ids
            if document_ids:
                folders_by_document = await run_blocking(
                    self.graph.folders_for_documents,
                    tenant=tenant,
                    document_ids=document_ids,
                )
                ranker.add_document_folders(folders_by_document)

        folder_scope_has_unsupported_filters = bool(
            scope
            and (
                scope.document_type
                or scope.document_id
                or scope.document_ids
                or scope.metadata_filter
            )
        )
        if not folder_scope_has_unsupported_filters:
            folder_vector_scope = (
                scope
                if scope
                and (scope.folder_ids or scope.created_at or scope.updated_at or scope.sort)
                else None
            )
            folder_results = await run_blocking(
                self.folder_vectors.search_folders,
                tenant=tenant,
                query_vector=vector,
                top_k=limit,
                scope=folder_vector_scope,
            )
            for folder_result in folder_results:
                ranker.add_folder_score(
                    folder=folder_result.folder,
                    score=folder_result.score,
                    reason=folder_result.reason or "Folder metadata is semantically close.",
                )
            async with self.retrieval_reads.session() as read:
                name_matches = await read.folder_sources.search_names_by_keyword(
                    tenant=tenant,
                    query_text=text.strip(),
                    top_k=limit,
                    folder_ids=scope.folder_ids if scope else (),
                    created_at=scope.created_at if scope else None,
                    updated_at=scope.updated_at if scope else None,
                )
                description_matches = (
                    await read.folder_sources.search_descriptions_by_keyword(
                        tenant=tenant,
                        query_text=text.strip(),
                        top_k=limit,
                        folder_ids=scope.folder_ids if scope else (),
                        created_at=scope.created_at if scope else None,
                        updated_at=scope.updated_at if scope else None,
                    )
                )
            for folder, score in name_matches:
                ranker.add_folder_score(
                    folder=folder,
                    score=score,
                    reason="Folder name matches keyword.",
                )
            for folder, score in description_matches:
                ranker.add_folder_score(
                    folder=folder,
                    score=score,
                    reason="Folder description matches keyword.",
                )

        return sort_by_timestamp_scope(
            ranker.results(),
            scope=scope,
            timestamp_value=lambda result, field: getattr(result.folder, field),
        )
