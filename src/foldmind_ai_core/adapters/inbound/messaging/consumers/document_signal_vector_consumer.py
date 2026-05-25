from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    delete_document_projection_command_from_outbox,
    project_document_command_from_outbox,
)
from foldmind_ai_core.core.application.ports.inbound.projection import (
    DocumentVectorProjectionServicePort,
)
from foldmind_ai_core.core.domain.models.outbox import OutboxEvent


@dataclass(slots=True)
class DocumentSignalVectorsIndexedConsumer:
    service: DocumentVectorProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.project_document_signals(
            project_document_command_from_outbox(event)
        )


@dataclass(slots=True)
class DocumentSignalVectorsDeletedConsumer:
    service: DocumentVectorProjectionServicePort

    async def consume_outbox_event(self, event: OutboxEvent) -> None:
        await self.service.delete_document_signals(
            delete_document_projection_command_from_outbox(event)
        )
