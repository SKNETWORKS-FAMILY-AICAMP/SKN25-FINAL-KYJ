from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.ports.outbound.session.indexing_write_session import (
    IndexingWriteSession,
)
from foldmind_ai_core.core.application.models.indexing import FolderSignalInvalidation
from foldmind_ai_core.core.domain.models.folder_index_state import (
    FolderIndexState,
    FolderSignalRefreshStatus,
)
from foldmind_ai_core.core.domain.services.folder_projection_digest_service import (
    FolderProjectionDigestService,
)


@dataclass(slots=True)
class FolderSignalInvalidationService:
    digest: FolderProjectionDigestService = field(
        default_factory=FolderProjectionDigestService
    )

    async def folder_index_record(
        self,
        *,
        tx: IndexingWriteSession,
        tenant: str,
        folder_id: str,
        refresh_status: FolderSignalRefreshStatus = (
            FolderSignalRefreshStatus.PENDING
        ),
    ) -> FolderIndexState:
        folder = await tx.folder_sources.get_current_folder_source(
            tenant=tenant,
            folder_id=folder_id,
        )
        signal_generation_version = (
            await tx.folder_projections.current_folder_signal_generation_version(
                folder_id=folder_id,
            )
        )
        folder_index_input_digest = self.digest.folder_index_input_digest(
            folder_id=folder_id,
            folder=folder,
        )
        folder_ids_in_subtree = await tx.folder_sources.active_folder_ids_in_subtree(
            tenant=tenant,
            folder_id=folder_id,
        )
        document_ids = await tx.document_relations.document_ids_for_folders(
            tenant=tenant,
            folder_ids=folder_ids_in_subtree,
        )
        document_sources = await tx.document_sources.get_current_document_sources(
            tenant=tenant,
            document_ids=document_ids,
        )
        document_index_states = (
            await tx.document_projections.get_current_document_index_records(
                document_ids=tuple(source.document_id for source in document_sources),
            )
        )
        folder_signal_input_digest = self.digest.folder_signal_input_digest(
            document_sources=document_sources,
            document_index_states=document_index_states,
            folder_index_input_digest=folder_index_input_digest,
            signal_generation_version=signal_generation_version,
        )
        return FolderIndexState(
            folder_id=folder_id,
            folder_index_input_digest=folder_index_input_digest,
            folder_signal_input_digest=folder_signal_input_digest,
            signal_generation_version=signal_generation_version,
            folder_signal_refresh_status=refresh_status,
        )

    async def invalidate(
        self,
        *,
        tx: IndexingWriteSession,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[FolderSignalInvalidation, ...]:
        folder_ids = tuple(sorted(set(folder_ids)))
        if not folder_ids:
            return ()

        await tx.folder_projections.delete_folder_signals_for_folder_ids(
            folder_ids=folder_ids,
        )
        invalidations: list[FolderSignalInvalidation] = []
        for folder_id in folder_ids:
            record = await self.folder_index_record(
                tx=tx,
                tenant=tenant,
                folder_id=folder_id,
            )
            signals_marked_pending = await tx.folder_projections.mark_folder_signals_pending(
                record=record,
            )
            if signals_marked_pending:
                invalidations.append(
                    FolderSignalInvalidation(
                        tenant=tenant,
                        folder_id=folder_id,
                        folder_signal_input_digest=record.folder_signal_input_digest,
                        signal_generation_version=record.signal_generation_version,
                    )
                )
        return tuple(invalidations)
