from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.application.services.outbox_events import folder_indexed_event
from foldmind_ai_core.domain.reference.folders import SourceFolder
from foldmind_ai_core.domain.retrieval.results import RetrievedFolder


@dataclass(slots=True)
class IndexFolderUseCase:
    indexing_uow: IndexingUnitOfWork

    def execute(self, folder: SourceFolder) -> RetrievedFolder:
        with self.indexing_uow.transaction() as tx:
            tx.append_outbox_event(folder_indexed_event(folder=folder))
        return RetrievedFolder(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
        )
