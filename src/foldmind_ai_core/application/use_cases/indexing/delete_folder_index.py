from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.application.services.outbox_events import folder_deleted_event


@dataclass(slots=True)
class DeleteFolderIndexUseCase:
    indexing_uow: IndexingUnitOfWork

    def execute(self, *, folder_id: str) -> None:
        with self.indexing_uow.transaction() as tx:
            tx.append_outbox_event(
                folder_deleted_event(
                    folder_id=folder_id,
                )
            )
