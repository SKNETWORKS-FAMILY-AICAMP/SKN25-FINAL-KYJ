from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.commands.indexing import IndexFolderCommand
from foldmind_ai_core.core.application.factories.source_snapshots import (
    source_folder_from_index_command,
)
from foldmind_ai_core.core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.core.application.results.indexing import IndexFolderResult
from foldmind_ai_core.core.application.services.outbox_events import folder_indexed_event


@dataclass(slots=True)
class IndexFolderUseCase:
    indexing_uow: IndexingUnitOfWork

    def execute(self, command: IndexFolderCommand) -> IndexFolderResult:
        folder = source_folder_from_index_command(command)
        with self.indexing_uow.transaction() as tx:
            tx.upsert_folder_index(folder=folder)
            tx.append_outbox_event(folder_indexed_event(folder=folder))
        return IndexFolderResult(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
        )
