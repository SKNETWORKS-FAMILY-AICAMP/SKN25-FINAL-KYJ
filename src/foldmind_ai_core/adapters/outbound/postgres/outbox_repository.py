from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from foldmind_ai_core.adapters.outbound.postgres.client import (
    PostgresClient,
    jsonb,
    row_value,
)
from foldmind_ai_core.domain.indexing.outbox import OutboxEvent

_INSERT_OUTBOX_EVENT_SQL = """
INSERT INTO outbox_events (
    id,
    aggregate_type,
    aggregate_id,
    event_key,
    event_type,
    event_schema_version,
    payload
)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""

_SELECT_LATEST_SEQUENCE_SQL = """
SELECT sequence
FROM outbox_events
WHERE aggregate_type = %s
  AND aggregate_id = %s
ORDER BY sequence DESC
LIMIT 1
"""


@dataclass(slots=True)
class PostgresOutboxRepository:
    client: PostgresClient

    def append(self, event: OutboxEvent) -> None:
        with self.client.connect() as conn:
            self.append_with_connection(conn, event)

    def append_with_connection(self, conn: Any, event: OutboxEvent) -> None:
        conn.execute(
            _INSERT_OUTBOX_EVENT_SQL,
            (
                event.id,
                event.aggregate_type,
                event.aggregate_id,
                event.event_key,
                event.event_type,
                event.event_schema_version,
                jsonb(event.payload),
            ),
        )

    def latest_sequence_for(
        self,
        *,
        aggregate_type: str,
        aggregate_id: str,
    ) -> int | None:
        with self.client.connect() as conn:
            row = conn.execute(
                _SELECT_LATEST_SEQUENCE_SQL,
                (aggregate_type, aggregate_id),
            ).fetchone()
        if row is None:
            return None
        return int(row_value(row, "sequence"))
