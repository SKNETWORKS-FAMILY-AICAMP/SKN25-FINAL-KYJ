from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument


class IndexedDocumentSourceRepository(Protocol):
    def get_current_document_source(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> SourceDocument | None:
        ...

    def get_current_document_folder_ids(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        ...
