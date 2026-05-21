from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.ports.outbound.vector_store import (
    VectorWriteResult,
)
from foldmind_ai_core.core.application.projections.vector import (
    DocumentChunkVectorProjection,
    DocumentSignalVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
)


class ProjectionLedger(Protocol):
    """Maintains current Qdrant point manifest records."""

    def record_document_vector_projected(
        self,
        *,
        projection: DocumentVectorProjection,
        write: VectorWriteResult,
    ) -> None:
        ...

    def record_chunk_vectors_projected(
        self,
        *,
        projections: tuple[DocumentChunkVectorProjection, ...],
        writes: tuple[VectorWriteResult, ...],
    ) -> None:
        ...

    def record_signal_vectors_projected(
        self,
        *,
        projections: tuple[DocumentSignalVectorProjection, ...],
        writes: tuple[VectorWriteResult, ...],
    ) -> None:
        ...

    def record_folder_signal_vectors_projected(
        self,
        *,
        projections: tuple[FolderSignalVectorProjection, ...],
        writes: tuple[VectorWriteResult, ...],
    ) -> None:
        ...

    def record_folder_vector_projected(
        self,
        *,
        projection: FolderVectorProjection,
        write: VectorWriteResult,
    ) -> None:
        ...

    def delete_document_vector_records(
        self,
        *,
        document_id: str,
    ) -> None:
        ...

    def delete_chunk_vector_records(
        self,
        *,
        document_id: str,
    ) -> None:
        ...

    def delete_signal_vector_records(
        self,
        *,
        document_id: str,
    ) -> None:
        ...

    def delete_folder_signal_vector_records(self, *, folder_id: str) -> None:
        ...

    def delete_stale_folder_signal_vector_records(
        self,
        *,
        folder_id: str,
        current_source_input_digest: str,
    ) -> None:
        ...

    def delete_folder_vector_records(self, *, folder_id: str) -> None:
        ...
