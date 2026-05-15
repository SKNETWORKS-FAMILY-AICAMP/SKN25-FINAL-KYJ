from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from foldmind_ai_core.domain.indexing.outbox import OutboxEvent, OutboxEventType


class OutboxEventConsumer(Protocol):
    def handle_outbox_event(self, event: OutboxEvent) -> None:
        ...


@dataclass(slots=True)
class IgnoreOutboxEventConsumer:
    def handle_outbox_event(self, event: OutboxEvent) -> None:
        pass


@dataclass(slots=True)
class OutboxEventDispatcher:
    document_indexed: OutboxEventConsumer
    document_deleted: OutboxEventConsumer
    folder_indexed: OutboxEventConsumer
    folder_deleted: OutboxEventConsumer

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        event_type = OutboxEventType(event.event_type)
        self._consumer_for(event_type).handle_outbox_event(event)

    def _consumer_for(self, event_type: OutboxEventType) -> OutboxEventConsumer:
        match event_type:
            case OutboxEventType.DOCUMENT_INDEXED:
                return self.document_indexed
            case OutboxEventType.DOCUMENT_DELETED:
                return self.document_deleted
            case OutboxEventType.FOLDER_INDEXED:
                return self.folder_indexed
            case OutboxEventType.FOLDER_DELETED:
                return self.folder_deleted
        raise ValueError(f"Unsupported outbox event type: {event_type.value}")
