from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.inbound.projection_use_case import (
    HandleDocumentChunkVectorDeletedProjectionUseCasePort,
    HandleDocumentChunkVectorIndexedProjectionUseCasePort,
)
from foldmind_ai_core.domain.indexing.outbox import OutboxEvent

from ..message_codec import (
    document_deleted_event_from_outbox,
    document_indexed_event_from_outbox,
)


@dataclass(slots=True)
class DocumentChunkVectorIndexedConsumer:
    use_case: HandleDocumentChunkVectorIndexedProjectionUseCasePort

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        projection_event = document_indexed_event_from_outbox(event)
        self.use_case.handle(projection_event)


@dataclass(slots=True)
class DocumentChunkVectorDeletedConsumer:
    use_case: HandleDocumentChunkVectorDeletedProjectionUseCasePort

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        projection_event = document_deleted_event_from_outbox(event)
        self.use_case.handle(projection_event)
