from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.folder_projections import (
    FolderSignalRow,
)


class FolderSignalStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_signals_for_folder(
        self,
        *,
        folder_id: str,
        rows: tuple[FolderSignalRow, ...],
    ) -> None:
        await self.delete_signals_for_folder(folder_id=folder_id)
        if rows:
            self.session.add_all(rows)

    async def delete_signals_for_folder(
        self,
        *,
        folder_id: str,
    ) -> None:
        await self.session.execute(
            delete(FolderSignalRow).where(FolderSignalRow.folder_id == folder_id)
        )

    async def delete_signals_for_folder_ids(
        self,
        *,
        folder_ids: tuple[str, ...],
    ) -> None:
        if not folder_ids:
            return
        await self.session.execute(
            delete(FolderSignalRow).where(FolderSignalRow.folder_id.in_(folder_ids))
        )

    async def folder_ids_with_signals_referencing_document(
        self,
        *,
        document_id: str,
    ) -> tuple[str, ...]:
        result = await self.session.execute(
            select(FolderSignalRow.folder_id)
            .where(FolderSignalRow.related_document_id == document_id)
            .order_by(FolderSignalRow.folder_id),
        )
        return tuple(result.scalars().all())
