from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.document_projections import (
    DocumentChunkRow,
)


DocumentChunkKeywordRow = tuple[DocumentChunkRow, float]


class DocumentChunkStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_chunks_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
        rows: tuple[DocumentChunkRow, ...],
    ) -> None:
        await self.delete_chunks_for_document(
            tenant=tenant,
            document_id=document_id,
        )
        if rows:
            self.session.add_all(rows)

    async def delete_chunks_for_document(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        await self.session.execute(
            delete(DocumentChunkRow)
            .where(DocumentChunkRow.tenant_id == tenant)
            .where(DocumentChunkRow.document_id == document_id),
        )

    async def first_chunk_rows_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
        limit: int,
    ) -> list[DocumentChunkRow]:
        if not document_ids or limit <= 0:
            return []
        result = await self.session.execute(
            select(DocumentChunkRow)
            .where(DocumentChunkRow.tenant_id == tenant)
            .where(DocumentChunkRow.document_id.in_(document_ids))
            .order_by(
                DocumentChunkRow.chunk_index.asc(),
                DocumentChunkRow.document_id.asc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def keyword_chunk_rows(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        document_id: str | None,
        document_ids: tuple[str, ...],
    ) -> list[DocumentChunkKeywordRow]:
        search_query = func.plainto_tsquery("simple", query_text)
        score = func.ts_rank_cd(
            func.setweight(DocumentChunkRow.search_vector, "B"),
            search_query,
        )
        conditions: list[object] = []
        if document_id is not None:
            conditions.append(DocumentChunkRow.document_id == document_id)
        if document_ids:
            conditions.append(DocumentChunkRow.document_id.in_(document_ids))

        result = await self.session.execute(
            select(DocumentChunkRow, score)
            .where(DocumentChunkRow.tenant_id == tenant)
            .where(DocumentChunkRow.search_vector.op("@@")(search_query))
            .where(*conditions)
            .order_by(score.desc(), DocumentChunkRow.chunk_index.asc())
            .limit(top_k)
        )
        return [
            (chunk_row, float(row_score))
            for chunk_row, row_score in result.all()
        ]
