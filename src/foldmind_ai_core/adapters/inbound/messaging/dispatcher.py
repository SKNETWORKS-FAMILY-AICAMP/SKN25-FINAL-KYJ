from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent, OutboxEventType


class OutboxEventConsumer(Protocol):
    def consume_outbox_event(self, event: OutboxEvent) -> None:
        ...


@dataclass(slots=True)
class OutboxEventDispatcher:
    document_indexed: OutboxEventConsumer | None
    document_deleted: OutboxEventConsumer | None
    folder_indexed: OutboxEventConsumer | None
    folder_deleted: OutboxEventConsumer | None
    document_folder_relations_indexed: OutboxEventConsumer | None = None
    folder_signals_indexed: OutboxEventConsumer | None = None
    folder_signals_invalidated: OutboxEventConsumer | None = None

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        event_type = OutboxEventType(event.event_type)
        match event_type:
            case OutboxEventType.DOCUMENT_INDEXED:
                consumer = self.document_indexed
            case OutboxEventType.DOCUMENT_FOLDER_RELATIONS_INDEXED:
                consumer = self.document_folder_relations_indexed
            case OutboxEventType.DOCUMENT_DELETED:
                consumer = self.document_deleted
            case OutboxEventType.FOLDER_INDEXED:
                consumer = self.folder_indexed
            case OutboxEventType.FOLDER_SIGNALS_INDEXED:
                consumer = self.folder_signals_indexed
            case OutboxEventType.FOLDER_SIGNALS_INVALIDATED:
                consumer = self.folder_signals_invalidated
            case OutboxEventType.FOLDER_DELETED:
                consumer = self.folder_deleted
        if consumer is not None:
            consumer.consume_outbox_event(event)
