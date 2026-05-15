from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.inbound.projection_use_case import (
    HandleDocumentVectorDeletedProjectionUseCasePort,
    HandleDocumentVectorIndexedProjectionUseCasePort,
)
from foldmind_ai_core.domain.indexing.outbox import OutboxEvent

from ..message_codec import (
    document_deleted_event_from_outbox,
    document_indexed_event_from_outbox,
)


@dataclass(slots=True)
class DocumentVectorIndexedConsumer:
    use_case: HandleDocumentVectorIndexedProjectionUseCasePort

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        projection_event = document_indexed_event_from_outbox(event)
        self.use_case.handle(projection_event)


@dataclass(slots=True)
class DocumentVectorDeletedConsumer:
    use_case: HandleDocumentVectorDeletedProjectionUseCasePort

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        projection_event = document_deleted_event_from_outbox(event)
        self.use_case.handle(projection_event)
