from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.sources import (
    SourceDocumentFolderRelationRow,
)


class DocumentFolderRelationStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_folder_relations_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
        rows: tuple[SourceDocumentFolderRelationRow, ...],
    ) -> None:
        await self.delete_folder_relations_for_document(
            tenant=tenant,
            document_id=document_id,
        )
        if rows:
            self.session.add_all(rows)

    async def delete_folder_relations_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        await self.session.execute(
            delete(SourceDocumentFolderRelationRow)
            .where(SourceDocumentFolderRelationRow.tenant_id == tenant)
            .where(SourceDocumentFolderRelationRow.document_id == document_id),
        )

    async def folder_ids_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        result = await self.session.execute(
            select(SourceDocumentFolderRelationRow.folder_id)
            .where(SourceDocumentFolderRelationRow.tenant_id == tenant)
            .where(SourceDocumentFolderRelationRow.document_id == document_id)
            .order_by(SourceDocumentFolderRelationRow.folder_id),
        )
        return tuple(result.scalars().all())

    async def document_ids_for_folders(
        self,
        *,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        if not folder_ids:
            return ()
        result = await self.session.execute(
            select(SourceDocumentFolderRelationRow.document_id)
            .where(SourceDocumentFolderRelationRow.tenant_id == tenant)
            .where(SourceDocumentFolderRelationRow.folder_id.in_(folder_ids))
            .distinct()
            .order_by(SourceDocumentFolderRelationRow.document_id),
        )
        return tuple(result.scalars().all())
