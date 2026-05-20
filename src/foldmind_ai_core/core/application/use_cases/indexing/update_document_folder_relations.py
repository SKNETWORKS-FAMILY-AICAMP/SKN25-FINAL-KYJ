from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.commands.indexing import (
    UpdateDocumentFolderRelationsCommand,
)
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.core.application.services.outbox_events import (
    document_folder_relations_indexed_event,
)
from foldmind_ai_core.core.application.models.indexing import (
    SourceDocumentFolderRelationSnapshot,
)


@dataclass(slots=True)
class UpdateDocumentFolderRelationsUseCase:
    indexing_uow: IndexingUnitOfWork

    def execute(self, command: UpdateDocumentFolderRelationsCommand) -> None:
        snapshot = SourceDocumentFolderRelationSnapshot(
            tenant=command.tenant,
            document_id=command.document_id,
            source_version=command.source_version,
            folder_ids=command.folder_ids,
        )
        with self.indexing_uow.transaction() as tx:
            updated = tx.replace_document_folder_relation_snapshot(snapshot=snapshot)
            if not updated:
                raise ResourceNotFoundError(
                    "Current indexed document source not found: "
                    f"{command.document_id}"
                )
            tx.append_outbox_event(document_folder_relations_indexed_event(snapshot))
