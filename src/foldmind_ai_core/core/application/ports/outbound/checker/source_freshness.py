from __future__ import annotations

from typing import Protocol


class SourceFreshnessChecker(Protocol):
    async def is_current_document_folder_relation_snapshot(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
    ) -> bool:
        ...

    async def is_current_document_index_input_digest(
        self,
        *,
        tenant: str,
        document_id: str,
        document_index_input_digest: str,
    ) -> bool:
        ...

    async def is_current_document_signal_input_digest(
        self,
        *,
        tenant: str,
        document_id: str,
        document_signal_input_digest: str,
        signal_generation_version: str,
    ) -> bool:
        ...

    async def is_current_folder_signal_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
        folder_signal_input_digest: str,
    ) -> bool:
        ...

    async def is_current_folder_index_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
        folder_index_input_digest: str,
    ) -> bool:
        ...
