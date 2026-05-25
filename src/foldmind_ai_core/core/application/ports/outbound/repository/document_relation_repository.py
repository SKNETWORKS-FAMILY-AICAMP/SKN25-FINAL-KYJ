from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)


class DocumentRelationRepositoryPort(Protocol):
    async def replace_folder_relations_for_document(
        self,
        *,
        snapshot: SourceDocumentFolderRelationSnapshot,
    ) -> None:
        ...

    async def get_folder_ids_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        ...

    async def document_ids_for_folders(
        self,
        *,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        ...

    async def delete_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        ...
