from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class ProjectionDocument:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    content_digest: str
    content_size_bytes: int
    created_at: str
    updated_at: str
    title: str = ""
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProjectionDocumentFolderRelationSnapshot:
    tenant: str
    document_id: str
    source_version: str
    folder_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectionSignalEvidence:
    chunk_id: str
    quote: str
    start_offset: int | None = None
    end_offset: int | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProjectionDocumentSignal:
    signal_id: str
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    content_digest: str
    document_signal_input_digest: str
    signal_type: str
    signal_key: str
    text: str
    signal_generation_version: str = "1"
    attributes: Metadata = field(default_factory=dict)
    evidence: tuple[ProjectionSignalEvidence, ...] = ()
    confidence: float | None = None
    extractor_name: str = ""
    extractor_version: str = ""
    generation_model: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProjectionFolderSignal:
    signal_id: str
    tenant: str
    folder_id: str
    source_version: str
    signal_type: str
    signal_key: str
    text: str
    related_document_id: str | None = None
    attributes: Metadata = field(default_factory=dict)
    evidence: tuple[Metadata, ...] = ()
    confidence: float | None = None
    extractor_name: str = ""
    extractor_version: str = ""
    folder_signal_input_digest: str = ""
    signal_generation_version: str = "1"
    metadata: Metadata = field(default_factory=dict)
    generation_model: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectionDocumentProfile:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    content_digest: str
    document_index_input_digest: str
    document_signal_input_digest: str
    created_at: str
    updated_at: str
    title: str
    signal_generation_version: str = "1"
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ProjectionFolder:
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
