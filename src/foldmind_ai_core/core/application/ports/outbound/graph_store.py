from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.projections.graph import (
    DocumentFolderRelationProjection,
    DocumentRelationshipProjection,
    DocumentSignalProjection,
    FolderSignalProjection,
    FolderRelationshipProjection,
)
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.domain.models.retrieval.results import (
    DocumentRetrievalResult,
    RetrievedFolder,
)


class GraphStore(Protocol):
    def replace_document_projection(
        self,
        *,
        relationships: DocumentRelationshipProjection,
        signals: DocumentSignalProjection,
    ) -> None:
        ...

    def replace_document_folder_relations(
        self,
        *,
        projection: DocumentFolderRelationProjection,
    ) -> None:
        ...

    def replace_folder_projection(
        self,
        *,
        relationships: FolderRelationshipProjection,
    ) -> None:
        ...

    def replace_folder_signals(
        self,
        *,
        signals: FolderSignalProjection,
    ) -> None:
        ...

    def document_ids_for_scope(
        self,
        *,
        tenant: str,
        scope: SearchScope,
    ) -> tuple[str, ...]:
        ...

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        ...

    def delete_document(
        self,
        *,
        document_id: str,
    ) -> None:
        ...

    def delete_folder_signals(self, *, folder_id: str) -> None:
        ...

    def delete_folder_signals_before_input_revision(
        self,
        *,
        folder_id: str,
        folder_signal_input_revision: int,
    ) -> None:
        ...

    def delete_folder(self, *, folder_id: str) -> None:
        ...

    def graph_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        """Return document candidates discovered through graph relationships."""
        ...
