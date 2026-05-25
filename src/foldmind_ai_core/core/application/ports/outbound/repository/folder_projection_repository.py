from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.folder_index_state import (
    FolderIndexState,
)
from foldmind_ai_core.core.domain.models.folder_signals import (
    FolderSignal,
)
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder


class FolderProjectionRepositoryPort(Protocol):
    async def upsert_folder_index_record(
        self,
        *,
        record: FolderIndexState,
    ) -> None:
        ...

    async def current_folder_signal_generation_version(
        self,
        *,
        folder_id: str,
    ) -> str:
        ...

    async def delete_folder_signals_for_folder_ids(
        self,
        *,
        folder_ids: tuple[str, ...],
    ) -> None:
        ...

    async def mark_folder_signals_pending(
        self,
        *,
        record: FolderIndexState,
    ) -> bool:
        ...

    async def current_folder_signal_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> str | None:
        ...

    async def folder_ids_with_signals_referencing_document(
        self,
        *,
        document_id: str,
    ) -> tuple[str, ...]:
        ...

    async def replace_folder_signals(
        self,
        *,
        folder: SourceFolder,
        signals: tuple[FolderSignal, ...],
        expected_folder_signal_input_digest: str,
        signal_generation_version: str,
    ) -> bool:
        ...

    async def mark_folder_projection_deleted(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> None:
        ...
