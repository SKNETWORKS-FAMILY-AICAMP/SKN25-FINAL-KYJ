from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from foldmind_ai_core.adapters.outbound.postgres.models.document_projections import (
    DocumentIndexRecordRow,
)


class DocumentIndexRecordStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_document_index_record(
        self,
        row: DocumentIndexRecordRow,
    ) -> None:
        await self.session.execute(_upsert_document_index_record_statement(row))

    async def mark_document_index_deleted(
        self,
        *,
        document_id: str,
        purge_after: datetime,
    ) -> None:
        await self.session.execute(
            update(DocumentIndexRecordRow)
            .where(DocumentIndexRecordRow.document_id == document_id)
            .values(
                deleted_at=func.coalesce(
                    DocumentIndexRecordRow.deleted_at,
                    func.now(),
                ),
                purge_after=func.coalesce(
                    DocumentIndexRecordRow.purge_after,
                    purge_after,
                ),
                updated_at=func.now(),
            )
        )

    async def current_document_index_exists(
        self,
        *,
        document_id: str,
    ) -> bool:
        result = await self.session.execute(
            _current_document_index_record_query(
                document_id=document_id,
            ),
        )
        return result.scalar_one_or_none() is not None

    async def document_index_input_digest_is_current(
        self,
        *,
        document_id: str,
        document_index_input_digest: str,
    ) -> bool:
        result = await self.session.execute(
            _current_document_index_record_query(
                document_id=document_id,
            ).where(
                DocumentIndexRecordRow.document_index_input_digest
                == document_index_input_digest
            )
        )
        return result.scalar_one_or_none() is not None

    async def document_signal_input_digest_is_current(
        self,
        *,
        document_id: str,
        document_signal_input_digest: str,
        signal_generation_version: str,
    ) -> bool:
        result = await self.session.execute(
            _current_document_index_record_query(
                document_id=document_id,
            )
            .where(
                DocumentIndexRecordRow.document_signal_input_digest
                == document_signal_input_digest
            )
            .where(
                DocumentIndexRecordRow.signal_generation_version
                == signal_generation_version
            )
        )
        return result.scalar_one_or_none() is not None

    async def current_document_index_record_rows(
        self,
        *,
        document_ids: tuple[str, ...],
    ) -> list[DocumentIndexRecordRow]:
        if not document_ids:
            return []
        result = await self.session.execute(
            select(DocumentIndexRecordRow)
            .where(DocumentIndexRecordRow.document_id.in_(document_ids))
            .where(DocumentIndexRecordRow.deleted_at.is_(None))
            .order_by(DocumentIndexRecordRow.document_id),
        )
        return list(result.scalars().all())


def _current_document_index_record_query(
    document_id: str,
) -> Select[tuple[int]]:
    return (
        select(1)
        .select_from(DocumentIndexRecordRow)
        .where(DocumentIndexRecordRow.document_id == document_id)
        .where(DocumentIndexRecordRow.deleted_at.is_(None))
        .limit(1)
    )


def _upsert_document_index_record_statement(row: DocumentIndexRecordRow) -> Insert:
    statement = insert(DocumentIndexRecordRow).values(
        document_id=row.document_id,
        document_index_input_digest=row.document_index_input_digest,
        document_signal_input_digest=row.document_signal_input_digest,
        signal_generation_version=row.signal_generation_version,
        deleted_at=None,
        purge_after=None,
        updated_at=func.now(),
    )
    excluded = statement.excluded
    return statement.on_conflict_do_update(
        index_elements=[DocumentIndexRecordRow.document_id],
        set_={
            "document_index_input_digest": excluded.document_index_input_digest,
            "document_signal_input_digest": excluded.document_signal_input_digest,
            "signal_generation_version": excluded.signal_generation_version,
            "deleted_at": None,
            "purge_after": None,
            "updated_at": func.now(),
        },
    )
