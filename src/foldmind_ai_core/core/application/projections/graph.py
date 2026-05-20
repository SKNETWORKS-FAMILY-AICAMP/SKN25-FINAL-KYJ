from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class DocumentRelationshipProjection:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    content_digest: str
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class DocumentFolderRelationProjection:
    tenant: str
    document_id: str
    source_version: str
    folder_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentSignalNodeProjection:
    signal_id: str
    tenant: str
    signal_type: str
    signal_key: str
    text: str
    document_id: str
    source_version: str
    content_digest: str
    attributes: Metadata = field(default_factory=dict)
    confidence: float | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentSignalProjection:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    content_digest: str
    created_at: str
    updated_at: str
    title: str
    signal_set_version: str
    signals: tuple[DocumentSignalNodeProjection, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FolderRelationshipProjection:
    tenant: str
    folder_id: str
    source_version: str
    name: str
    created_at: str
    updated_at: str
    path: str | None = None
    parent_folder_id: str | None = None


@dataclass(frozen=True, slots=True)
class FolderSignalNodeProjection:
    signal_id: str
    tenant: str
    folder_id: str
    source_version: str
    signal_type: str
    signal_key: str
    text: str
    related_document_id: str | None = None
    attributes: Metadata = field(default_factory=dict)
    confidence: float | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FolderSignalProjection:
    tenant: str
    folder_id: str
    source_version: str
    signals: tuple[FolderSignalNodeProjection, ...] = ()
