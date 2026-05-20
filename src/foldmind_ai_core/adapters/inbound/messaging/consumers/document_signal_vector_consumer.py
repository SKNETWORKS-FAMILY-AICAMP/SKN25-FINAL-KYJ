from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.inbound.messaging.mappers.outbox import (
    delete_document_projection_command,
    project_document_command,
)
from foldmind_ai_core.core.application.ports.inbound.projection import (
    DeleteDocumentSignalVectorsInboundPort,
    ProjectDocumentSignalVectorsInboundPort,
)
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent


@dataclass(slots=True)
class DocumentSignalVectorsIndexedConsumer:
    use_case: ProjectDocumentSignalVectorsInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(project_document_command(event))


@dataclass(slots=True)
class DocumentSignalVectorsDeletedConsumer:
    use_case: DeleteDocumentSignalVectorsInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(delete_document_projection_command(event))
