from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.application.services.outbox_events import document_deleted_event


@dataclass(slots=True)
class DeleteDocumentIndexUseCase:
    indexing_uow: IndexingUnitOfWork

    def execute(self, *, document_id: str) -> None:
        with self.indexing_uow.transaction() as tx:
            tx.delete_document_profile(document_id=document_id)
            tx.append_outbox_event(
                document_deleted_event(
                    document_id=document_id,
                )
            )
