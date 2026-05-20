from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.inbound.messaging.mappers.outbox import (
    delete_folder_projection_command,
    project_folder_command,
)
from foldmind_ai_core.core.application.ports.inbound.projection import (
    DeleteFolderSignalVectorsInboundPort,
    ProjectFolderSignalVectorsInboundPort,
)
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent


@dataclass(slots=True)
class FolderSignalVectorsIndexedConsumer:
    use_case: ProjectFolderSignalVectorsInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(project_folder_command(event))


@dataclass(slots=True)
class FolderSignalVectorsDeletedConsumer:
    use_case: DeleteFolderSignalVectorsInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(delete_folder_projection_command(event))
