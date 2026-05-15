from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.application.ports.outbound.vector_repository import (
    DocumentChunkVectorRepository,
)
from foldmind_ai_core.domain.indexing.projection_events import (
    DocumentDeletedProjectionEvent,
    DocumentIndexedProjectionEvent,
)


@dataclass(slots=True)
class HandleDocumentChunkVectorIndexedProjectionUseCase:
    embeddings: EmbeddingProvider
    chunk_vectors: DocumentChunkVectorRepository

    def handle(self, event: DocumentIndexedProjectionEvent) -> None:
        vectors = self.embeddings.embed_texts([chunk.text for chunk in event.chunks])
        self.chunk_vectors.replace_document_chunks(
            document_id=event.document.document_id,
            chunks=event.chunks,
            vectors=tuple(vectors),
        )


@dataclass(slots=True)
class HandleDocumentChunkVectorDeletedProjectionUseCase:
    chunk_vectors: DocumentChunkVectorRepository

    def handle(self, event: DocumentDeletedProjectionEvent) -> None:
        self.chunk_vectors.delete_document_chunks(document_id=event.document_id)
