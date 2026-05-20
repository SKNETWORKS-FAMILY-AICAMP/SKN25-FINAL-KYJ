from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class IndexDocumentCommand:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    title: str
    body: str
    created_at: str
    updated_at: str
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DeleteDocumentIndexCommand:
    document_id: str


@dataclass(frozen=True, slots=True)
class UpdateDocumentFolderRelationsCommand:
    tenant: str
    document_id: str
    source_version: str
    folder_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IndexFolderCommand:
    tenant: str
    folder_id: str
    source_version: str
    name: str
    created_at: str
    updated_at: str
    path: str | None = None
    parent_folder_id: str | None = None
    description: str = ""
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DeleteFolderIndexCommand:
    folder_id: str


@dataclass(frozen=True, slots=True)
class EvaluateFolderResponsibilityCommand:
    tenant: str
    folder_id: str
