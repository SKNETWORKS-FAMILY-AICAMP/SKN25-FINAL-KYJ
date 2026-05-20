from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.ports.inbound.projection import (
    DeleteDocumentGraphInboundPort,
    DeleteFolderGraphInboundPort,
    ProjectDocumentFolderRelationsGraphInboundPort,
    ProjectDocumentGraphInboundPort,
    ProjectFolderGraphInboundPort,
)
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent
from foldmind_ai_core.adapters.inbound.messaging.mappers.outbox import (
    delete_document_projection_command,
    delete_folder_projection_command,
    project_document_folder_relations_command,
    project_document_command,
    project_folder_command,
)


@dataclass(slots=True)
class DocumentGraphIndexedConsumer:
    use_case: ProjectDocumentGraphInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(project_document_command(event))


@dataclass(slots=True)
class DocumentGraphFolderRelationsIndexedConsumer:
    use_case: ProjectDocumentFolderRelationsGraphInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(project_document_folder_relations_command(event))


@dataclass(slots=True)
class DocumentGraphDeletedConsumer:
    use_case: DeleteDocumentGraphInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(delete_document_projection_command(event))


@dataclass(slots=True)
class FolderGraphIndexedConsumer:
    use_case: ProjectFolderGraphInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(project_folder_command(event))


@dataclass(slots=True)
class FolderGraphDeletedConsumer:
    use_case: DeleteFolderGraphInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(delete_folder_projection_command(event))
