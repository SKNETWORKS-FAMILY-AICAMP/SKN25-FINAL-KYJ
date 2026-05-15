from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.application.ports.outbound.vector_repository import (
    DocumentVectorRepository,
)
from foldmind_ai_core.application.services.vector_projection_spec import VectorProjectionSpec
from foldmind_ai_core.domain.indexing.projection_events import (
    DocumentDeletedProjectionEvent,
    DocumentIndexedProjectionEvent,
)
from foldmind_ai_core.domain.reference.documents import DocumentVectorProjection


@dataclass(slots=True)
class HandleDocumentVectorIndexedProjectionUseCase:
    embeddings: EmbeddingProvider
    document_vectors: DocumentVectorRepository
    projection_spec: VectorProjectionSpec

    def handle(self, event: DocumentIndexedProjectionEvent) -> None:
        projection = DocumentVectorProjection.from_profile(
            event.profile,
            embedding_model=self.projection_spec.embedding_model,
            embedding_version=self.projection_spec.embedding_version,
            index_schema_version=self.projection_spec.index_schema_version,
        )
        vector = self.embeddings.embed_texts([projection.embedding_input])[0]
        self.document_vectors.upsert_document_vector(
            projection=projection,
            vector=vector,
        )


@dataclass(slots=True)
class HandleDocumentVectorDeletedProjectionUseCase:
    document_vectors: DocumentVectorRepository

    def handle(self, event: DocumentDeletedProjectionEvent) -> None:
        self.document_vectors.delete_document_vector(document_id=event.document_id)
