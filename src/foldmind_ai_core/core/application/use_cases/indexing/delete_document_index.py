from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.commands.indexing import DeleteDocumentIndexCommand
from foldmind_ai_core.core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.core.application.services.outbox_events import (
    document_deleted_event,
    folder_signals_invalidated_event,
)


@dataclass(slots=True)
class DeleteDocumentIndexUseCase:
    indexing_uow: IndexingUnitOfWork

    def execute(self, command: DeleteDocumentIndexCommand) -> None:
        with self.indexing_uow.transaction() as tx:
            deleted = tx.mark_document_deleted(
                document_id=command.document_id,
            )
            if deleted is not None:
                tx.append_outbox_event(
                    document_deleted_event(
                        tenant=deleted.tenant,
                        document_id=deleted.document_id,
                        affected_folder_ids=deleted.affected_folder_ids,
                    )
                )
                for invalidation in deleted.folder_signal_invalidations:
                    tx.append_outbox_event(folder_signals_invalidated_event(invalidation))
