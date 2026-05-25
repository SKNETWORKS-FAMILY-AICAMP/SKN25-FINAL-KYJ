from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.postgres.mappers.outbox import (
    outbox_event_row_from_model,
)
from foldmind_ai_core.adapters.outbound.postgres.store.outbox_store import (
    OutboxEventStore,
)
from foldmind_ai_core.core.domain.models.outbox import OutboxEvent


@dataclass(slots=True)
class OutboxRepository:
    outbox_events: OutboxEventStore

    async def append(self, event: OutboxEvent) -> None:
        row = outbox_event_row_from_model(event)
        await self.outbox_events.append_outbox_event(row)
