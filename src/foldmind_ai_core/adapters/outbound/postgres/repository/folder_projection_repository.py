from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.adapters.outbound.postgres.mappers.document_signal import (
    folder_signal_row_from_domain,
)
from foldmind_ai_core.adapters.outbound.postgres.mappers.indexing import (
    folder_index_state_row_from_domain,
)
from foldmind_ai_core.adapters.outbound.postgres.policies.retention_policy import (
    PurgeAfterPolicy,
)
from foldmind_ai_core.adapters.outbound.postgres.store.folder_index_record_store import (
    FolderIndexRecordStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.folder_signal_store import (
    FolderSignalStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.folder_source_store import (
    FolderSourceStore,
)
from foldmind_ai_core.core.domain.models.folder_index_state import (
    FolderIndexState,
)
from foldmind_ai_core.core.domain.models.folder_signals import (
    FolderSignal,
)
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder


_DEFAULT_SIGNAL_GENERATION_VERSION = "1"


@dataclass(slots=True)
class FolderProjectionRepository:
    folder_sources: FolderSourceStore
    folder_index_records: FolderIndexRecordStore
    folder_signals: FolderSignalStore
    purge_after_policy: PurgeAfterPolicy = field(default_factory=PurgeAfterPolicy)

    async def upsert_folder_index_record(
        self,
        *,
        record: FolderIndexState,
    ) -> None:
        await self.folder_index_records.upsert_folder_index_record(
            folder_index_state_row_from_domain(record)
        )

    async def current_folder_signal_generation_version(
        self,
        *,
        folder_id: str,
    ) -> str:
        version = await self.folder_index_records.current_folder_signal_generation_version(
            folder_id=folder_id,
        )
        return version or _DEFAULT_SIGNAL_GENERATION_VERSION

    async def delete_folder_signals_for_folder_ids(
        self,
        *,
        folder_ids: tuple[str, ...],
    ) -> None:
        await self.folder_signals.delete_signals_for_folder_ids(
            folder_ids=tuple(sorted(set(folder_ids))),
        )

    async def mark_folder_signals_pending(
        self,
        *,
        record: FolderIndexState,
    ) -> bool:
        return await self.folder_index_records.mark_folder_signals_pending(
            folder_id=record.folder_id,
            folder_index_input_digest=record.folder_index_input_digest,
            folder_signal_input_digest=record.folder_signal_input_digest,
        )

    async def current_folder_signal_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> str | None:
        source_row = await self.folder_sources.current_folder_source_row(
            tenant=tenant,
            folder_id=folder_id,
        )
        if source_row is None:
            return None
        return await self.folder_index_records.current_folder_signal_input_digest(
            folder_id=folder_id,
        )

    async def folder_ids_with_signals_referencing_document(
        self,
        *,
        document_id: str,
    ) -> tuple[str, ...]:
        return await self.folder_signals.folder_ids_with_signals_referencing_document(
            document_id=document_id,
        )

    async def replace_folder_signals(
        self,
        *,
        folder: SourceFolder,
        signals: tuple[FolderSignal, ...],
        expected_folder_signal_input_digest: str,
        signal_generation_version: str,
    ) -> bool:
        source_row = await self.folder_sources.current_folder_source_row(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
        )
        if source_row is None:
            return False

        current_digest = await (
            self.folder_index_records.current_folder_signal_input_digest(
                folder_id=folder.folder_id,
            )
        )
        if current_digest != expected_folder_signal_input_digest:
            return False

        signals_marked_ready = await (
            self.folder_index_records.mark_folder_signals_ready(
                folder_id=folder.folder_id,
                folder_signal_input_digest=expected_folder_signal_input_digest,
                signal_generation_version=signal_generation_version,
            )
        )
        if not signals_marked_ready:
            return False

        await self.folder_signals.replace_signals_for_folder(
            folder_id=folder.folder_id,
            rows=tuple(folder_signal_row_from_domain(signal) for signal in signals),
        )
        return True

    async def mark_folder_projection_deleted(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> None:
        await self.folder_signals.delete_signals_for_folder(
            folder_id=folder_id,
        )
        await self.folder_index_records.mark_folder_index_deleted(
            folder_id=folder_id,
            purge_after=self.purge_after_policy.purge_after(),
        )
