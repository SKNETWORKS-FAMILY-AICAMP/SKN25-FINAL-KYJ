from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.application.ports.outbound.graph_repository import GraphRepository
from foldmind_ai_core.application.ports.outbound.vector_repository import (
    DocumentChunkVectorRepository,
    DocumentVectorRepository,
    FolderVectorRepository,
)
from foldmind_ai_core.application.services.folder_retrieval_ranker import (
    FolderRetrievalRanker,
)
from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import FolderRetrievalResult
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class FolderRetrievalService:
    embeddings: EmbeddingProvider
    chunk_vectors: DocumentChunkVectorRepository
    document_vectors: DocumentVectorRepository
    folder_vectors: FolderVectorRepository
    graph: GraphRepository
    top_k: int = 5
    candidate_multiplier: int = 4

    def __post_init__(self) -> None:
        if self.top_k <= 0:
            raise InvalidInputError("top_k must be greater than 0.")
        if self.candidate_multiplier <= 0:
            raise InvalidInputError("candidate_multiplier must be greater than 0.")

    def search(
        self,
        *,
        tenant: str,
        text: str,
        scope: SearchScope | None,
        document_search_scope: SearchScope | None,
        excluded_folder_ids: tuple[str, ...] = (),
    ) -> list[FolderRetrievalResult]:
        vector = self.embeddings.embed_texts([text])[0]
        limit = self.top_k * self.candidate_multiplier
        ranker = FolderRetrievalRanker(
            top_k=self.top_k,
            excluded_folder_ids=excluded_folder_ids,
        )

        for result in self.document_vectors.search_documents(
            tenant=tenant,
            query_vector=vector,
            top_k=limit,
            scope=document_search_scope,
        ):
            ranker.add_document_signal(
                document_id=result.document.document_id,
                score=result.score,
                reason="Similar indexed document belongs to this folder.",
            )

        for result in self.chunk_vectors.search_chunks(
            tenant=tenant,
            query_vector=vector,
            top_k=limit,
            scope=document_search_scope,
        ):
            ranker.add_document_signal(
                document_id=result.chunk.document_id,
                score=result.score,
                reason="Similar indexed chunk belongs to this folder.",
            )

        for result in self.folder_vectors.search_folders(
            tenant=tenant,
            query_vector=vector,
            top_k=limit,
            scope=scope,
        ):
            ranker.add_folder_score(
                folder=result.folder,
                score=result.score,
                reason=result.reason or "Folder metadata is semantically close.",
            )

        for result in self.graph.graph_search(
            tenant=tenant,
            query_text=text,
            top_k=limit,
            scope=scope,
        ):
            ranker.add_document_signal(
                document_id=result.document.document_id,
                score=result.score,
                reason="Graph-related document belongs to this folder.",
            )

        if ranker.document_ids:
            ranker.add_document_folders(
                self.graph.folders_for_documents(
                    tenant=tenant,
                    document_ids=ranker.document_ids,
                )
            )

        return ranker.results()
