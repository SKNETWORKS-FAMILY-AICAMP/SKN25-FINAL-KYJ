from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    delete_folder_projection_command_from_outbox,
    project_folder_command_from_outbox,
)
from foldmind_ai_core.core.application.ports.inbound.projection import (
    FolderVectorProjectionServicePort,
)
from foldmind_ai_core.core.domain.models.outbox import OutboxEvent


@dataclass(slots=True)
class FolderVectorIndexedConsumer:
    service: FolderVectorProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.project_folder_vector(
            project_folder_command_from_outbox(event)
        )


@dataclass(slots=True)
class FolderVectorDeletedConsumer:
    service: FolderVectorProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.delete_folder_vector(
            delete_folder_projection_command_from_outbox(event)
        )
