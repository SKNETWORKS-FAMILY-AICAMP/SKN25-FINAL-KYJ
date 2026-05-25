from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.document_projections import (
    DocumentSignalRow,
)


class DocumentSignalStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_signals_for_document(
        self,
        *,
        document_id: str,
        rows: tuple[DocumentSignalRow, ...],
    ) -> None:
        await self.delete_signals_for_document(document_id=document_id)
        if rows:
            self.session.add_all(rows)

    async def delete_signals_for_document(
        self,
        *,
        document_id: str,
    ) -> None:
        await self.session.execute(
            delete(DocumentSignalRow).where(DocumentSignalRow.document_id == document_id)
        )

    async def signal_text_rows_for_document(
        self,
        *,
        document_id: str,
    ) -> list[DocumentSignalRow]:
        result = await self.session.execute(
            select(DocumentSignalRow)
            .where(DocumentSignalRow.document_id == document_id),
        )
        return list(result.scalars().all())
