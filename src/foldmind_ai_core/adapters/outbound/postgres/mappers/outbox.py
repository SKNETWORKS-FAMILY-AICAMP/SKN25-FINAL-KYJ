from __future__ import annotations

from foldmind_ai_core.adapters.outbound.postgres.models.outbox import (
    OutboxEventRow,
)
from foldmind_ai_core.core.domain.models.outbox import OutboxEvent


def outbox_event_row_from_model(event: OutboxEvent) -> OutboxEventRow:
    return OutboxEventRow(
        event_id=event.event_id,
        tenant_id=event.tenant,
        source_kind=event.source_kind,
        source_id=event.source_id,
        event_type=event.event_type,
        payload_schema_version=event.payload_schema_version,
        idempotency_key=event.idempotency_key,
        payload=dict(event.payload),
    )
