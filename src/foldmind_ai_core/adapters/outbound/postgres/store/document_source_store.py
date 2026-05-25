from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.sources import (
    DocumentSourceRow,
)


DocumentTitleKeywordRow = tuple[DocumentSourceRow, float]


class DocumentSourceStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_document_source(
        self,
        row: DocumentSourceRow,
    ) -> None:
        await self.session.execute(_upsert_document_source_statement(row))

    async def document_source_is_current(
        self,
        *,
        document_id: str,
        tenant: str,
        source_version: str,
        content_digest: str,
    ) -> bool:
        result = await self.session.execute(
            select(1)
            .select_from(DocumentSourceRow)
            .where(DocumentSourceRow.document_id == document_id)
            .where(DocumentSourceRow.tenant_id == tenant)
            .where(DocumentSourceRow.source_version == source_version)
            .where(DocumentSourceRow.content_digest == content_digest)
            .where(DocumentSourceRow.deleted_at.is_(None))
            .limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def current_document_source_row(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> DocumentSourceRow | None:
        result = await self.session.execute(
            select(DocumentSourceRow)
            .where(DocumentSourceRow.tenant_id == tenant)
            .where(DocumentSourceRow.document_id == document_id)
            .where(DocumentSourceRow.deleted_at.is_(None)),
        )
        return result.scalar_one_or_none()

    async def document_source_version_is_current(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
    ) -> bool:
        result = await self.session.execute(
            select(1)
            .select_from(DocumentSourceRow)
            .where(DocumentSourceRow.tenant_id == tenant)
            .where(DocumentSourceRow.document_id == document_id)
            .where(DocumentSourceRow.source_version == source_version)
            .where(DocumentSourceRow.deleted_at.is_(None))
            .limit(1),
        )
        return result.scalar_one_or_none() is not None

    async def current_document_source_version_for_update(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> str | None:
        result = await self.session.execute(
            select(DocumentSourceRow.source_version)
            .where(DocumentSourceRow.tenant_id == tenant)
            .where(DocumentSourceRow.document_id == document_id)
            .where(DocumentSourceRow.deleted_at.is_(None))
            .with_for_update()
            .limit(1),
        )
        source_version = result.scalar_one_or_none()
        if source_version is None:
            return None
        return str(source_version)

    async def document_source_row_for_delete(
        self,
        document_id: str,
    ) -> DocumentSourceRow | None:
        result = await self.session.execute(
            select(DocumentSourceRow)
            .where(DocumentSourceRow.document_id == document_id)
            .where(DocumentSourceRow.deleted_at.is_(None)),
        )
        return result.scalar_one_or_none()

    async def mark_document_source_deleted(
        self,
        *,
        tenant: str,
        document_id: str,
        purge_after: datetime,
    ) -> None:
        await self.session.execute(
            update(DocumentSourceRow)
            .where(DocumentSourceRow.tenant_id == tenant)
            .where(DocumentSourceRow.document_id == document_id)
            .values(
                deleted_at=func.coalesce(DocumentSourceRow.deleted_at, func.now()),
                purge_after=func.coalesce(
                    DocumentSourceRow.purge_after,
                    purge_after,
                ),
                updated_at=func.now(),
            ),
        )

    async def current_document_source_rows(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> list[DocumentSourceRow]:
        if not document_ids:
            return []
        result = await self.session.execute(
            select(DocumentSourceRow)
            .where(DocumentSourceRow.tenant_id == tenant)
            .where(DocumentSourceRow.deleted_at.is_(None))
            .where(DocumentSourceRow.document_id.in_(document_ids))
            .order_by(DocumentSourceRow.document_id)
        )
        return list(result.scalars().all())

    async def current_document_ids(
        self,
        *,
        tenant: str,
        document_type: str | None,
        document_id: str | None,
        document_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
        metadata_filter: dict[str, Any] | None,
    ) -> tuple[str, ...]:
        conditions: list[object] = []
        if document_type is not None:
            conditions.append(DocumentSourceRow.document_type == document_type)
        if document_id is not None:
            conditions.append(DocumentSourceRow.document_id == document_id)
        if document_ids:
            conditions.append(DocumentSourceRow.document_id.in_(document_ids))
        if created_at is not None:
            conditions.append(DocumentSourceRow.source_created_at == created_at)
        if updated_at is not None:
            conditions.append(DocumentSourceRow.source_updated_at == updated_at)
        if metadata_filter:
            conditions.append(DocumentSourceRow.metadata_json.contains(metadata_filter))

        result = await self.session.execute(
            select(DocumentSourceRow.document_id)
            .where(DocumentSourceRow.tenant_id == tenant)
            .where(DocumentSourceRow.deleted_at.is_(None))
            .where(*conditions)
            .order_by(DocumentSourceRow.document_id)
        )
        return tuple(result.scalars().all())

    async def keyword_title_rows(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        document_type: str | None,
        document_id: str | None,
        document_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
        metadata_filter: dict[str, Any] | None,
    ) -> list[DocumentTitleKeywordRow]:
        search_query = func.plainto_tsquery("simple", query_text)
        score = func.ts_rank_cd(
            func.setweight(DocumentSourceRow.title_search_vector, "A"),
            search_query,
        )
        conditions: list[object] = []
        if document_type is not None:
            conditions.append(DocumentSourceRow.document_type == document_type)
        if document_id is not None:
            conditions.append(DocumentSourceRow.document_id == document_id)
        if document_ids:
            conditions.append(DocumentSourceRow.document_id.in_(document_ids))
        if created_at is not None:
            conditions.append(DocumentSourceRow.source_created_at == created_at)
        if updated_at is not None:
            conditions.append(DocumentSourceRow.source_updated_at == updated_at)
        if metadata_filter:
            conditions.append(DocumentSourceRow.metadata_json.contains(metadata_filter))

        result = await self.session.execute(
            select(DocumentSourceRow, score)
            .where(DocumentSourceRow.tenant_id == tenant)
            .where(DocumentSourceRow.deleted_at.is_(None))
            .where(DocumentSourceRow.title_search_vector.op("@@")(search_query))
            .where(*conditions)
            .order_by(score.desc(), DocumentSourceRow.source_updated_at.desc())
            .limit(top_k)
        )
        return [(source_row, float(row_score)) for source_row, row_score in result.all()]


def _upsert_document_source_statement(row: DocumentSourceRow) -> Insert:
    statement = insert(DocumentSourceRow).values(
        document_id=row.document_id,
        tenant_id=row.tenant_id,
        document_type=row.document_type,
        source_version=row.source_version,
        source_created_at=row.source_created_at,
        source_updated_at=row.source_updated_at,
        title=row.title,
        content_digest=row.content_digest,
        content_size_bytes=row.content_size_bytes,
        metadata_json=row.metadata_json,
        updated_at=func.now(),
    )
    excluded = statement.excluded
    current_or_newer_source = (
        (DocumentSourceRow.source_version == excluded.source_version)
        | (DocumentSourceRow.source_updated_at < excluded.source_updated_at)
    )
    return statement.on_conflict_do_update(
        index_elements=[DocumentSourceRow.document_id],
        set_={
            "tenant_id": excluded.tenant_id,
            "document_type": excluded.document_type,
            "source_version": excluded.source_version,
            "source_created_at": excluded.source_created_at,
            "source_updated_at": excluded.source_updated_at,
            "title": excluded.title,
            "content_digest": excluded.content_digest,
            "content_size_bytes": excluded.content_size_bytes,
            "metadata_json": excluded.metadata_json,
            "deleted_at": None,
            "purge_after": None,
            "updated_at": func.now(),
        },
        where=current_or_newer_source,
    )
