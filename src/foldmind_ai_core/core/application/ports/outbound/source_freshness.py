from __future__ import annotations

from typing import Protocol


class SourceFreshnessChecker(Protocol):
    def is_current_document_source(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
        content_digest: str,
    ) -> bool:
        raise NotImplementedError

    def is_current_folder_source(
        self,
        *,
        tenant: str,
        folder_id: str,
        source_version: str,
    ) -> bool:
        raise NotImplementedError

    def is_current_document_folder_relation_snapshot(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
    ) -> bool:
        raise NotImplementedError
