from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder


class FolderResponsibilitySourceRepository(Protocol):
    def get_folder_source(self, *, tenant: str, folder_id: str) -> SourceFolder | None:
        ...

    def list_member_document_sources(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> tuple[SourceDocument, ...]:
        ...
