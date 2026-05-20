from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.ports.inbound.projection import (
    DeleteFolderVectorInboundPort,
    ProjectFolderVectorInboundPort,
)
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent
from foldmind_ai_core.adapters.inbound.messaging.mappers.outbox import (
    delete_folder_projection_command,
    project_folder_command,
)


@dataclass(slots=True)
class FolderVectorIndexedConsumer:
    use_case: ProjectFolderVectorInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(project_folder_command(event))


@dataclass(slots=True)
class FolderVectorDeletedConsumer:
    use_case: DeleteFolderVectorInboundPort

    def consume_outbox_event(self, event: OutboxEvent) -> None:
        self.use_case.execute(delete_folder_projection_command(event))
