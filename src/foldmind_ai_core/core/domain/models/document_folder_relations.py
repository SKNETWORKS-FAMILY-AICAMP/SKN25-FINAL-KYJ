from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceDocumentFolderRelationSnapshot:
    tenant: str
    document_id: str
    source_version: str
    folder_ids: tuple[str, ...] = ()

