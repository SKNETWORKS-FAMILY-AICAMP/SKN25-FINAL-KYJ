from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.ports.inbound.projection import (
    DeleteDocumentVectorInboundPort,
    ProjectDocumentVectorInboundPort,
)
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent
from foldmind_ai_core.adapters.inbound.messaging.mappers.outbox import (
    delete_document_projection_command,
    project_document_command,
)


@dataclass(slots=True)
class DocumentVectorIndexedConsumer:
    use_case: ProjectDocumentVectorInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(project_document_command(event))


@dataclass(slots=True)
class DocumentVectorDeletedConsumer:
    use_case: DeleteDocumentVectorInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(delete_document_projection_command(event))
