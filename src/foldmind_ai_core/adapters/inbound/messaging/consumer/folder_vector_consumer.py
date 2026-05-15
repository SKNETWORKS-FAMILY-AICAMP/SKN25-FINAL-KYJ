from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.inbound.projection_use_case import (
    HandleFolderVectorDeletedProjectionUseCasePort,
    HandleFolderVectorIndexedProjectionUseCasePort,
)
from foldmind_ai_core.domain.indexing.outbox import OutboxEvent

from ..message_codec import (
    folder_deleted_event_from_outbox,
    folder_indexed_event_from_outbox,
)


@dataclass(slots=True)
class FolderVectorIndexedConsumer:
    use_case: HandleFolderVectorIndexedProjectionUseCasePort

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        projection_event = folder_indexed_event_from_outbox(event)
        self.use_case.handle(projection_event)


@dataclass(slots=True)
class FolderVectorDeletedConsumer:
    use_case: HandleFolderVectorDeletedProjectionUseCasePort

    def handle_outbox_event(self, event: OutboxEvent) -> None:
        projection_event = folder_deleted_event_from_outbox(event)
        self.use_case.handle(projection_event)
