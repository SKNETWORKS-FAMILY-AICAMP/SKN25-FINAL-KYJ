from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.postgres.mappers.indexing import (
    source_document_folder_relation_rows_from_snapshot,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_folder_relation_store import (
    DocumentFolderRelationStore,
)
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)


@dataclass(slots=True)
class DocumentRelationRepository:
    document_folder_relations: DocumentFolderRelationStore

    async def replace_folder_relations_for_document(
        self,
        *,
        snapshot: SourceDocumentFolderRelationSnapshot,
    ) -> None:
        await self.document_folder_relations.replace_folder_relations_for_document(
            tenant=snapshot.tenant,
            document_id=snapshot.document_id,
            rows=source_document_folder_relation_rows_from_snapshot(snapshot),
        )

    async def get_folder_ids_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        return await self.document_folder_relations.folder_ids_for_document(
            tenant=tenant,
            document_id=document_id,
        )

    async def document_ids_for_folders(
        self,
        *,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        return await self.document_folder_relations.document_ids_for_folders(
            tenant=tenant,
            folder_ids=folder_ids,
        )

    async def delete_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        await self.document_folder_relations.delete_folder_relations_for_document(
            tenant=tenant,
            document_id=document_id,
        )
