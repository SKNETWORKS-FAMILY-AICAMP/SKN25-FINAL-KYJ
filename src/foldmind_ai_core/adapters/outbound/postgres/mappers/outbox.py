from __future__ import annotations

from foldmind_ai_core.adapters.outbound.postgres.models.outbox import (
    PostgresOutboxEventRecord,
)
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent


def outbox_event_record_from_domain(event: OutboxEvent) -> PostgresOutboxEventRecord:
    return PostgresOutboxEventRecord(
        event_id=event.event_id,
        tenant=event.tenant,
        source_kind=event.source_kind,
        source_id=event.source_id,
        event_type=event.event_type,
        payload_schema_version=event.payload_schema_version,
        idempotency_key=event.idempotency_key,
        payload=dict(event.payload),
    )
