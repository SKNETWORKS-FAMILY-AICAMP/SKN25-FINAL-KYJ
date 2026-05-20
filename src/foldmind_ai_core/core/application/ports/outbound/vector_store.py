from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from foldmind_ai_core.core.application.projections.vector import (
    DocumentChunkVectorProjection,
    DocumentSignalVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
)
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.domain.models.retrieval.results import (
    DocumentRetrievalResult,
    FolderRetrievalResult,
    RetrievalResult,
    SignalRetrievalResult,
)
from foldmind_ai_core.shared.types import Vector


@dataclass(frozen=True, slots=True)
class VectorWriteResult:
    collection_name: str
    point_id: str
    payload_digest: str


class DocumentChunkVectorStore(Protocol):
    def replace_document_chunks(
        self,
        *,
        tenant: str,
        document_id: str,
        chunks: tuple[DocumentChunkVectorProjection, ...],
        vectors: tuple[Vector, ...],
    ) -> tuple[VectorWriteResult, ...]:
        """Replace chunk-level vectors for one document."""
        ...

    def delete_document_chunks(
        self,
        *,
        document_id: str,
    ) -> None:
        """Delete chunk-level vectors for one document."""
        ...

    def search_chunks(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        """Return top-k chunk-level dense matches."""
        ...


class DocumentVectorStore(Protocol):
    def upsert_document_vector(
        self,
        *,
        projection: DocumentVectorProjection,
        vector: Vector,
    ) -> VectorWriteResult:
        """Insert or update a document-level vector projection."""
        ...

    def delete_document_vector(
        self,
        *,
        document_id: str,
    ) -> None:
        """Delete a document-level vector projection."""
        ...

    def search_documents(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        """Return top-k document-level dense candidates."""
        ...


class SignalVectorStore(Protocol):
    def replace_document_signals(
        self,
        *,
        tenant: str,
        document_id: str,
        signals: tuple[DocumentSignalVectorProjection, ...],
        vectors: tuple[Vector, ...],
    ) -> tuple[VectorWriteResult, ...]:
        """Replace signal-level vectors for one document."""
        ...

    def delete_document_signals(
        self,
        *,
        document_id: str,
    ) -> None:
        """Delete signal-level vectors for one document."""
        ...

    def replace_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        signals: tuple[FolderSignalVectorProjection, ...],
        vectors: tuple[Vector, ...],
    ) -> tuple[VectorWriteResult, ...]:
        """Replace signal-level vectors for one folder."""
        ...

    def delete_folder_signals(
        self,
        *,
        folder_id: str,
    ) -> None:
        """Delete signal-level vectors for one folder."""
        ...

    def delete_stale_folder_signals(
        self,
        *,
        folder_id: str,
        current_index_input_digest: str,
    ) -> None:
        """Delete stale folder signal vectors not matching the current digest."""
        ...

    def search_signals(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        signal_type: str | None = None,
        scope: SearchScope | None = None,
    ) -> list[SignalRetrievalResult]:
        """Return top-k signal-level dense candidates."""
        ...


class FolderVectorStore(Protocol):
    def upsert_folder_vector(
        self,
        *,
        projection: FolderVectorProjection,
        vector: Vector,
    ) -> VectorWriteResult:
        """Insert or update a folder semantic vector projection."""
        ...

    def delete_folder_vector(self, *, folder_id: str) -> None:
        """Delete a folder semantic vector projection."""
        ...

    def search_folders(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[FolderRetrievalResult]:
        """Return top-k relevant folders."""
        ...
