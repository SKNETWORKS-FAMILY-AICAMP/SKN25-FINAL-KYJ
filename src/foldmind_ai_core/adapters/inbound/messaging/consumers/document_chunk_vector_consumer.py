from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.ports.inbound.projection import (
    DeleteDocumentChunkVectorsInboundPort,
    ProjectDocumentChunkVectorsInboundPort,
)
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent
from foldmind_ai_core.adapters.inbound.messaging.mappers.outbox import (
    delete_document_projection_command,
    project_document_command,
)


@dataclass(slots=True)
class DocumentChunkVectorIndexedConsumer:
    use_case: ProjectDocumentChunkVectorsInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(project_document_command(event))


@dataclass(slots=True)
class DocumentChunkVectorDeletedConsumer:
    use_case: DeleteDocumentChunkVectorsInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(delete_document_projection_command(event))
