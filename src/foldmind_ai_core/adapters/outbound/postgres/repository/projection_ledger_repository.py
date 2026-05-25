from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.postgres.mappers.projection_ledger import (
    vector_projection_record_row,
)
from foldmind_ai_core.adapters.outbound.postgres.store.projection_ledger_store import (
    VectorProjectionRecordStore,
)
from foldmind_ai_core.core.domain.models.vector_projection_state import (
    VectorProjectionState,
)


@dataclass(slots=True)
class ProjectionLedgerRepository:
    vector_projection_records: VectorProjectionRecordStore

    async def record_document_vector_projected(
        self,
        *,
        record: VectorProjectionState,
    ) -> None:
        await self._record_projection_records((record,))

    async def replace_chunk_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
        records: tuple[VectorProjectionState, ...],
    ) -> None:
        await self.delete_chunk_vector_records(
            tenant=tenant,
            document_id=document_id,
        )
        await self._record_projection_records(records)

    async def replace_signal_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
        records: tuple[VectorProjectionState, ...],
    ) -> None:
        await self.delete_signal_vector_records(
            tenant=tenant,
            document_id=document_id,
        )
        await self._record_projection_records(records)

    async def replace_folder_signal_vector_records(
        self,
        *,
        tenant: str,
        folder_id: str,
        records: tuple[VectorProjectionState, ...],
    ) -> None:
        await self.delete_folder_signal_vector_records(
            tenant=tenant,
            folder_id=folder_id,
        )
        await self._record_projection_records(records)

    async def record_folder_vector_projected(
        self,
        *,
        record: VectorProjectionState,
    ) -> None:
        await self._record_projection_records((record,))

    async def _record_projection_records(
        self,
        records: tuple[VectorProjectionState, ...],
    ) -> None:
        for record in records:
            await self.vector_projection_records.upsert_projection_record(
                vector_projection_record_row(record)
            )

    async def delete_document_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        await self._delete_records_for_source(
            tenant=tenant,
            source_kind="document",
            source_id=document_id,
            vector_item_kinds=("document",),
        )

    async def delete_chunk_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        await self._delete_records_for_source(
            tenant=tenant,
            source_kind="document",
            source_id=document_id,
            vector_item_kinds=("chunk",),
        )

    async def delete_signal_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        await self._delete_records_for_source(
            tenant=tenant,
            source_kind="document",
            source_id=document_id,
            vector_item_kinds=("signal",),
        )

    async def delete_folder_signal_vector_records(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> None:
        await self._delete_records_for_source(
            tenant=tenant,
            source_kind="folder",
            source_id=folder_id,
            vector_item_kinds=("signal",),
        )

    async def delete_stale_folder_signal_vector_records(
        self,
        *,
        tenant: str,
        folder_id: str,
        current_source_input_digest: str,
    ) -> None:
        await self.vector_projection_records.delete_stale_projection_records(
            tenant=tenant,
            source_kind="folder",
            source_id=folder_id,
            vector_item_kind="signal",
            current_source_input_digest=current_source_input_digest,
        )

    async def delete_folder_vector_records(self, *, tenant: str, folder_id: str) -> None:
        await self._delete_records_for_source(
            tenant=tenant,
            source_kind="folder",
            source_id=folder_id,
            vector_item_kinds=("folder",),
        )

    async def _delete_records_for_source(
        self,
        *,
        tenant: str,
        source_kind: str,
        source_id: str,
        vector_item_kinds: tuple[str, ...],
    ) -> None:
        await self.vector_projection_records.delete_projection_records_for_source(
            tenant=tenant,
            source_kind=source_kind,
            source_id=source_id,
            vector_item_kinds=vector_item_kinds,
        )
