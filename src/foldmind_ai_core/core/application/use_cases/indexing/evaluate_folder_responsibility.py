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
from foldmind_ai_core.core.application.services.outbox_events import (
    folder_signals_indexed_event,
)
from foldmind_ai_core.core.domain.models.profiling import FolderSignal
from foldmind_ai_core.core.domain.services.profiling import folder_signal_id


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
        with self.indexing_uow.transaction() as tx:
            target_folder_signal_input_digest = tx.current_folder_signal_input_digest(
                tenant=command.tenant,
                folder_id=command.folder_id,
            )
        if target_folder_signal_input_digest is None:
            raise ResourceNotFoundError(
                f"Folder index record not found: {command.folder_id}"
            )
        member_documents = self.source_repository.list_member_document_sources(
            tenant=command.tenant,
            folder_id=command.folder_id,
        )
        extraction = self.signal_extractor.evaluate(folder, member_documents)
        signals = _with_folder_signal_input_digest(
            extraction.signals,
            folder_signal_input_digest=target_folder_signal_input_digest,
            signal_generation_version=extraction.signal_generation_version,
        )
        with self.indexing_uow.transaction() as tx:
            commit = tx.replace_folder_signals(
                folder=folder,
                signals=signals,
                expected_folder_signal_input_digest=target_folder_signal_input_digest,
                signal_generation_version=extraction.signal_generation_version,
            )
            if commit.applied:
                tx.append_outbox_event(
                    folder_signals_indexed_event(
                        folder=folder,
                        folder_signal_input_digest=commit.folder_signal_input_digest,
                        signal_generation_version=extraction.signal_generation_version,
                        signals=signals,
                    )
                )
        signal_count = len(signals) if commit.applied else 0
        return EvaluateFolderResponsibilityResult(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
            signal_count=signal_count,
        )


def _with_folder_signal_input_digest(
    signals: tuple[FolderSignal, ...],
    *,
    folder_signal_input_digest: str,
    signal_generation_version: str,
) -> tuple[FolderSignal, ...]:
    return tuple(
        replace(
            signal,
            signal_id=folder_signal_id(
                tenant=signal.tenant,
                folder_id=signal.folder_id,
                folder_signal_input_digest=folder_signal_input_digest,
                signal_generation_version=signal_generation_version,
                signal_type=signal.signal_type,
                signal_key=signal.signal_key,
                related_document_id=signal.related_document_id,
            ),
            folder_signal_input_digest=folder_signal_input_digest,
            signal_generation_version=signal_generation_version,
        )
        for signal in signals
    )
