from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeletedDocumentIdentity:
    tenant: str
    document_id: str
    affected_folder_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DeletedFolderIdentity:
    tenant: str
    folder_id: str


@dataclass(frozen=True, slots=True)
class SourceDocumentFolderRelationSnapshot:
    tenant: str
    document_id: str
    source_version: str
    folder_ids: tuple[str, ...] = ()
