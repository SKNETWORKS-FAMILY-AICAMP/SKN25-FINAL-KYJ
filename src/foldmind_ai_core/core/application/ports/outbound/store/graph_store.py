from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.document_signals import DocumentSignal
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.domain.models.folder_signals import FolderSignal
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.application.models.search import SearchScope
from foldmind_ai_core.core.application.models.retrieval import (
    DocumentRetrievalResult,
)


class GraphStore(Protocol):
    def replace_document_projection(
        self,
        *,
        document: DocumentSourceState,
        document_index: DocumentIndexState,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        ...

    def replace_document_folder_relations(
        self,
        *,
        projection: SourceDocumentFolderRelationSnapshot,
    ) -> None:
        ...

    def replace_folder_projection(
        self,
        *,
        folder: SourceFolder,
    ) -> None:
        ...

    def replace_folder_signals(
        self,
        *,
        folder: SourceFolder,
        folder_signal_input_digest: str,
        signal_generation_version: str,
        signals: tuple[FolderSignal, ...],
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
    ) -> dict[str, tuple[SourceFolder, ...]]:
        ...

    def delete_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        ...

    def delete_folder_signals(self, *, tenant: str, folder_id: str) -> None:
        ...

    def delete_stale_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        current_folder_signal_input_digest: str,
    ) -> None:
        ...

    def delete_folder(self, *, tenant: str, folder_id: str) -> None:
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
