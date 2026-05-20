from __future__ import annotations

from dataclasses import dataclass, replace

from foldmind_ai_core.core.application.capabilities.profiling import FolderSignalExtractor
from foldmind_ai_core.core.application.commands.indexing import (
    EvaluateFolderResponsibilityCommand,
)
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.ports.outbound.folder_responsibility_sources import (
    FolderResponsibilitySourceRepository,
)
from foldmind_ai_core.core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.core.application.results.indexing import (
    EvaluateFolderResponsibilityResult,
)
from foldmind_ai_core.core.application.services.outbox_events import folder_indexed_event
from foldmind_ai_core.core.domain.models.profiling import FolderSignal


@dataclass(slots=True)
class EvaluateFolderResponsibilityUseCase:
    source_repository: FolderResponsibilitySourceRepository
    signal_extractor: FolderSignalExtractor
    indexing_uow: IndexingUnitOfWork

    def execute(
        self,
        command: EvaluateFolderResponsibilityCommand,
    ) -> EvaluateFolderResponsibilityResult:
        folder = self.source_repository.get_folder_source(
            tenant=command.tenant,
            folder_id=command.folder_id,
        )
        if folder is None:
            raise ResourceNotFoundError(f"Folder source not found: {command.folder_id}")
        member_documents = self.source_repository.list_member_document_sources(
            tenant=command.tenant,
            folder_id=command.folder_id,
        )
        extraction = self.signal_extractor.evaluate(folder, member_documents)
        signals = _with_extraction_metadata(
            extraction.signals,
            signal_set_version=extraction.signal_set_version,
            model=extraction.model,
        )
        with self.indexing_uow.transaction() as tx:
            tx.upsert_folder_index(folder=folder, signals=signals)
            tx.append_outbox_event(folder_indexed_event(folder=folder, signals=signals))
        return EvaluateFolderResponsibilityResult(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
            signal_count=len(signals),
        )


def _with_extraction_metadata(
    signals: tuple[FolderSignal, ...],
    *,
    signal_set_version: str,
    model: str,
) -> tuple[FolderSignal, ...]:
    return tuple(
        replace(
            signal,
            metadata={
                **signal.metadata,
                "signal_set_version": signal_set_version,
                "model": model,
            },
        )
        for signal in signals
    )
