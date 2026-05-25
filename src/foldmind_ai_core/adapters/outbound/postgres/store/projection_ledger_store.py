from __future__ import annotations

from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.vector_projection_ledger import (
    VectorProjectionRecordRow,
)


class VectorProjectionRecordStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_projection_record(self, row: VectorProjectionRecordRow) -> None:
        await self.session.execute(_upsert_projection_record_statement(row))

    async def delete_projection_records_for_source(
        self,
        *,
        tenant: str,
        source_kind: str,
        source_id: str,
        vector_item_kinds: tuple[str, ...],
    ) -> None:
        await self.session.execute(
            delete(VectorProjectionRecordRow)
            .where(VectorProjectionRecordRow.tenant_id == tenant)
            .where(VectorProjectionRecordRow.source_kind == source_kind)
            .where(VectorProjectionRecordRow.source_id == source_id)
            .where(VectorProjectionRecordRow.vector_item_kind.in_(vector_item_kinds)),
        )

    async def delete_stale_projection_records(
        self,
        *,
        tenant: str,
        source_kind: str,
        source_id: str,
        vector_item_kind: str,
        current_source_input_digest: str,
    ) -> None:
        await self.session.execute(
            delete(VectorProjectionRecordRow)
            .where(VectorProjectionRecordRow.tenant_id == tenant)
            .where(VectorProjectionRecordRow.source_kind == source_kind)
            .where(VectorProjectionRecordRow.source_id == source_id)
            .where(VectorProjectionRecordRow.vector_item_kind == vector_item_kind)
            .where(
                VectorProjectionRecordRow.source_input_digest
                != current_source_input_digest
            ),
        )


def _upsert_projection_record_statement(row: VectorProjectionRecordRow) -> Insert:
    statement = insert(VectorProjectionRecordRow).values(
        tenant_id=row.tenant_id,
        collection_name=row.collection_name,
        point_id=row.point_id,
        source_kind=row.source_kind,
        source_id=row.source_id,
        vector_item_kind=row.vector_item_kind,
        vector_item_id=row.vector_item_id,
        source_input_digest=row.source_input_digest,
        vector_input_digest=row.vector_input_digest,
        updated_at=func.now(),
    )
    excluded = statement.excluded
    return statement.on_conflict_do_update(
        index_elements=[
            VectorProjectionRecordRow.tenant_id,
            VectorProjectionRecordRow.collection_name,
            VectorProjectionRecordRow.source_kind,
            VectorProjectionRecordRow.source_id,
            VectorProjectionRecordRow.vector_item_kind,
            VectorProjectionRecordRow.vector_item_id,
        ],
        set_={
            "point_id": excluded.point_id,
            "source_input_digest": excluded.source_input_digest,
            "vector_input_digest": excluded.vector_input_digest,
            "updated_at": func.now(),
        },
    )
