from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.commands.indexing import DeleteFolderIndexCommand
from foldmind_ai_core.core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.core.application.services.outbox_events import folder_deleted_event


@dataclass(slots=True)
class DeleteFolderIndexUseCase:
    indexing_uow: IndexingUnitOfWork

    def execute(self, command: DeleteFolderIndexCommand) -> None:
        with self.indexing_uow.transaction() as tx:
            deleted = tx.mark_folder_deleted(
                folder_id=command.folder_id,
            )
            if deleted is not None:
                tx.append_outbox_event(
                    folder_deleted_event(
                        tenant=deleted.tenant,
                        folder_id=deleted.folder_id,
                    )
                )
