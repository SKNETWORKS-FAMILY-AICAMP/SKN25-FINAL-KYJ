from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.reference.documents import DocumentVectorProjection
from foldmind_ai_core.domain.reference.folders import FolderVectorProjection
from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import (
    DocumentRetrievalResult,
    FolderRetrievalResult,
    RetrievalResult,
)
from foldmind_ai_core.shared.types import Vector


class DocumentChunkVectorRepository(Protocol):
    def replace_document_chunks(
        self,
        *,
        document_id: str,
        chunks: tuple[DocumentChunk, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
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


class DocumentKeywordRepository(Protocol):
    def upsert_keywords(self, chunks: tuple[DocumentChunk, ...]) -> None:
        """Insert or update keyword-searchable document chunks."""
        ...

    def delete_document_keywords(
        self,
        *,
        document_id: str,
    ) -> None:
        """Delete keyword-searchable chunks for one document."""
        ...

    def search_keywords(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        """Return top-k chunk-level keyword matches."""
        ...


class DocumentVectorRepository(Protocol):
    def upsert_document_vector(
        self,
        *,
        projection: DocumentVectorProjection,
        vector: Vector,
    ) -> None:
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


class FolderVectorRepository(Protocol):
    def upsert_folder_vector(
        self,
        *,
        projection: FolderVectorProjection,
        vector: Vector,
    ) -> None:
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
