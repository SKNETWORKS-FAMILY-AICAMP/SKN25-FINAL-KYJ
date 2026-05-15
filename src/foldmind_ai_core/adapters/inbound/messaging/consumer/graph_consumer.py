from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.inbound.projection_use_case import (
    HandleDocumentGraphDeletedProjectionUseCasePort,
    HandleDocumentGraphIndexedProjectionUseCasePort,
    HandleFolderGraphDeletedProjectionUseCasePort,
    HandleFolderGraphIndexedProjectionUseCasePort,
)
from foldmind_ai_core.domain.indexing.outbox import OutboxEvent

from ..message_codec import (
    document_deleted_event_from_outbox,
    document_indexed_event_from_outbox,
    folder_deleted_event_from_outbox,
    folder_indexed_event_from_outbox,
)


@dataclass(slots=True)
class DocumentGraphIndexedConsumer:
    use_case: HandleDocumentGraphIndexedProjectionUseCasePort

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        projection_event = document_indexed_event_from_outbox(event)
        self.use_case.handle(projection_event)


@dataclass(slots=True)
class DocumentGraphDeletedConsumer:
    use_case: HandleDocumentGraphDeletedProjectionUseCasePort

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        projection_event = document_deleted_event_from_outbox(event)
        self.use_case.handle(projection_event)


@dataclass(slots=True)
class FolderGraphIndexedConsumer:
    use_case: HandleFolderGraphIndexedProjectionUseCasePort

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        projection_event = folder_indexed_event_from_outbox(event)
        self.use_case.handle(projection_event)


@dataclass(slots=True)
class FolderGraphDeletedConsumer:
    use_case: HandleFolderGraphDeletedProjectionUseCasePort

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        projection_event = folder_deleted_event_from_outbox(event)
        self.use_case.handle(projection_event)
