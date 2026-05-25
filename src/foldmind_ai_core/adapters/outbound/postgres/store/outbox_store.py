from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.outbox import OutboxEventRow


class OutboxEventStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append_outbox_event(self, row: OutboxEventRow) -> None:
        await self.session.execute(
            insert(OutboxEventRow)
            .values(
                event_id=row.event_id,
                tenant_id=row.tenant_id,
                source_kind=row.source_kind,
                source_id=row.source_id,
                event_type=row.event_type,
                payload_schema_version=row.payload_schema_version,
                idempotency_key=row.idempotency_key,
                payload=row.payload,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    OutboxEventRow.tenant_id,
                    OutboxEventRow.idempotency_key,
                ]
            )
        )
