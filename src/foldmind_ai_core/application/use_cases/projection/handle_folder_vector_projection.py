from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.application.ports.outbound.vector_repository import (
    FolderVectorRepository,
)
from foldmind_ai_core.application.services.vector_projection_spec import VectorProjectionSpec
from foldmind_ai_core.domain.indexing.projection_events import (
    FolderDeletedProjectionEvent,
    FolderIndexedProjectionEvent,
)
from foldmind_ai_core.domain.reference.folders import FolderVectorProjection


@dataclass(slots=True)
class HandleFolderVectorIndexedProjectionUseCase:
    embeddings: EmbeddingProvider
    folder_vectors: FolderVectorRepository
    projection_spec: VectorProjectionSpec

    def handle(self, event: FolderIndexedProjectionEvent) -> None:
        projection = FolderVectorProjection.from_source(
            event.folder,
            embedding_model=self.projection_spec.embedding_model,
            embedding_version=self.projection_spec.embedding_version,
            index_schema_version=self.projection_spec.index_schema_version,
        )
        vector = self.embeddings.embed_texts([projection.embedding_input])[0]
        self.folder_vectors.upsert_folder_vector(projection=projection, vector=vector)


@dataclass(slots=True)
class HandleFolderVectorDeletedProjectionUseCase:
    folder_vectors: FolderVectorRepository

    def handle(self, event: FolderDeletedProjectionEvent) -> None:
        self.folder_vectors.delete_folder_vector(folder_id=event.folder_id)
