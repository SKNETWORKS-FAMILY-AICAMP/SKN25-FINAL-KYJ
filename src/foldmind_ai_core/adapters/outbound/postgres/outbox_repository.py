from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient, jsonb
from foldmind_ai_core.adapters.outbound.postgres.mappers.outbox import (
    outbox_event_record_from_domain,
)
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent

_INSERT_OUTBOX_EVENT_SQL = """
INSERT INTO outbox_events (
    event_id,
    tenant_id,
    source_kind,
    source_id,
    event_type,
    payload_schema_version,
    idempotency_key,
    payload
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (tenant_id, idempotency_key)
DO NOTHING
"""

@dataclass(slots=True)
class PostgresOutboxRepository:
    client: PostgresClient

    def append(self, event: OutboxEvent) -> None:
        with self.client.connect() as conn:
            self.append_with_connection(conn, event)

    def append_with_connection(self, conn: Any, event: OutboxEvent) -> None:
        record = outbox_event_record_from_domain(event)
        conn.execute(
            _INSERT_OUTBOX_EVENT_SQL,
            (
                record.event_id,
                record.tenant,
                record.source_kind,
                record.source_id,
                record.event_type,
                record.payload_schema_version,
                record.idempotency_key,
                jsonb(record.payload),
            ),
        )
