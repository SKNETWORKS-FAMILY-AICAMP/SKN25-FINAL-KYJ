from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.models.indexing import (
    DeleteFolderIndexCommand,
    FolderSignalInvalidation,
)
from foldmind_ai_core.core.application.mappers.outbox_events import (
    folder_deleted_event,
    folder_indexed_event,
    folder_signals_invalidated_event,
)
from foldmind_ai_core.core.application.ports.outbound.session.indexing_write_session import (
    IndexingWriteSession,
    IndexingWriteSessionProvider,
)
from foldmind_ai_core.core.application.services.indexing.folder_signal_invalidation_service import (
    FolderSignalInvalidationService,
)
from foldmind_ai_core.core.domain.models.folder_sources import (
    FolderSourceIdentity,
    SourceFolder,
)


@dataclass(frozen=True, slots=True)
class _FolderIndexWrite:
    applied: bool
    folder_signal_invalidations: tuple[FolderSignalInvalidation, ...] = ()


@dataclass(frozen=True, slots=True)
class _DeletedFolder:
    tenant: str
    folder_id: str
    source_version: str
    folder_signal_invalidations: tuple[FolderSignalInvalidation, ...] = ()


@dataclass(slots=True)
class FolderIndexingService:
    indexing: IndexingWriteSessionProvider
    folder_signal_invalidator: FolderSignalInvalidationService = field(
        default_factory=FolderSignalInvalidationService
    )

    async def index_folder(self, folder: SourceFolder) -> FolderSourceIdentity:
        async with self.indexing.transaction() as tx:
            change = await self._replace_index(tx=tx, folder=folder)
            if change.applied:
                await tx.outbox.append(folder_indexed_event(folder=folder))
                for invalidation in change.folder_signal_invalidations:
                    await tx.outbox.append(
                        folder_signals_invalidated_event(invalidation)
                    )
        return FolderSourceIdentity(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
        )

    async def delete_folder(self, command: DeleteFolderIndexCommand) -> None:
        async with self.indexing.transaction() as tx:
            deleted = await self._mark_deleted(tx=tx, folder_id=command.folder_id)
            if deleted is not None:
                await tx.outbox.append(
                    folder_deleted_event(
                        tenant=deleted.tenant,
                        folder_id=deleted.folder_id,
                        source_version=deleted.source_version,
                    )
                )
                for invalidation in deleted.folder_signal_invalidations:
                    await tx.outbox.append(
                        folder_signals_invalidated_event(invalidation)
                    )

    async def _replace_index(
        self,
        *,
        tx: IndexingWriteSession,
        folder: SourceFolder,
    ) -> _FolderIndexWrite:
        previous_folder = await tx.folder_sources.get_current_folder_source(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
        )
        source_is_current = await tx.folder_sources.upsert_folder_source(folder)
        if not source_is_current:
            return _FolderIndexWrite(applied=False)
        affected_folder_ids = await self._affected_folder_ids_after_source_upsert(
            tx=tx,
            previous_folder=previous_folder,
            folder=folder,
        )
        record = await self.folder_signal_invalidator.folder_index_record(
            tx=tx,
            tenant=folder.tenant,
            folder_id=folder.folder_id,
        )
        await tx.folder_projections.upsert_folder_index_record(record=record)
        invalidations = await self.folder_signal_invalidator.invalidate(
            tx=tx,
            tenant=folder.tenant,
            folder_ids=tuple(sorted({folder.folder_id, *affected_folder_ids})),
        )
        return _FolderIndexWrite(
            applied=True,
            folder_signal_invalidations=invalidations,
        )

    async def _affected_folder_ids_after_source_upsert(
        self,
        *,
        tx: IndexingWriteSession,
        previous_folder: SourceFolder | None,
        folder: SourceFolder,
    ) -> tuple[str, ...]:
        previous_parent_id = (
            previous_folder.parent_folder_id if previous_folder is not None else None
        )
        if previous_folder is not None and previous_parent_id == folder.parent_folder_id:
            return (folder.folder_id,)

        old_parent_ancestors = await tx.folder_sources.ancestor_folder_ids(
            tenant=folder.tenant,
            folder_ids=((previous_parent_id,) if previous_parent_id is not None else ()),
        )
        current_ancestors = await tx.folder_sources.ancestor_folder_ids(
            tenant=folder.tenant,
            folder_ids=(folder.folder_id,),
        )
        return tuple(
            sorted({folder.folder_id, *old_parent_ancestors, *current_ancestors})
        )

    async def _mark_deleted(
        self,
        *,
        tx: IndexingWriteSession,
        folder_id: str,
    ) -> _DeletedFolder | None:
        identity = await tx.folder_sources.folder_identity_for_delete(folder_id)
        if identity is None:
            return None

        affected_folder_ids = await tx.folder_sources.ancestor_folder_ids(
            tenant=identity.tenant,
            folder_ids=(identity.folder_id,),
        )
        await tx.folder_projections.mark_folder_projection_deleted(
            tenant=identity.tenant,
            folder_id=identity.folder_id,
        )
        await tx.folder_sources.mark_folder_source_deleted(
            tenant=identity.tenant,
            folder_id=identity.folder_id,
        )
        ancestor_folder_ids = tuple(
            folder_id
            for folder_id in affected_folder_ids
            if folder_id != identity.folder_id
        )
        invalidations = await self.folder_signal_invalidator.invalidate(
            tx=tx,
            tenant=identity.tenant,
            folder_ids=ancestor_folder_ids,
        )
        return _DeletedFolder(
            tenant=identity.tenant,
            folder_id=identity.folder_id,
            source_version=identity.source_version,
            folder_signal_invalidations=invalidations,
        )
