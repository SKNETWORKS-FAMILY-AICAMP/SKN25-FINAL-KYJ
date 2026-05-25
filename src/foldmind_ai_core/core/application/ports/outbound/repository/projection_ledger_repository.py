from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.vector_projection_state import (
    VectorProjectionState,
)


class ProjectionLedgerRepositoryPort(Protocol):
    async def record_document_vector_projected(
        self,
        *,
        record: VectorProjectionState,
    ) -> None:
        ...

    async def replace_chunk_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
        records: tuple[VectorProjectionState, ...],
    ) -> None:
        ...

    async def replace_signal_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
        records: tuple[VectorProjectionState, ...],
    ) -> None:
        ...

    async def replace_folder_signal_vector_records(
        self,
        *,
        tenant: str,
        folder_id: str,
        records: tuple[VectorProjectionState, ...],
    ) -> None:
        ...

    async def record_folder_vector_projected(
        self,
        *,
        record: VectorProjectionState,
    ) -> None:
        ...

    async def delete_document_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        ...

    async def delete_chunk_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        ...

    async def delete_signal_vector_records(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        ...

    async def delete_folder_signal_vector_records(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> None:
        ...

    async def delete_stale_folder_signal_vector_records(
        self,
        *,
        tenant: str,
        folder_id: str,
        current_source_input_digest: str,
    ) -> None:
        ...

    async def delete_folder_vector_records(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> None:
        ...
