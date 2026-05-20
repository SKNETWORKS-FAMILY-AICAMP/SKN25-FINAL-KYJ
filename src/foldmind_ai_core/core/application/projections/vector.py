from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.models.projection_inputs import (
    ProjectionSignalEvidence,
)
from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class DocumentChunkVectorProjection:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    content_digest: str
    index_input_digest: str
    created_at: str
    updated_at: str
    chunk_id: str
    chunk_index: int
    chunking_version: str
    text: str
    text_hash: str
    start_offset: int
    end_offset: int
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DocumentVectorProjection:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    content_digest: str
    index_input_digest: str
    created_at: str
    updated_at: str
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str


@dataclass(frozen=True, slots=True)
class DocumentSignalVectorProjection:
    signal_id: str
    tenant: str
    document_type: str | None
    document_id: str
    signal_type: str
    signal_key: str
    source_version: str
    content_digest: str
    index_input_digest: str
    attributes: Metadata
    confidence: float | None
    evidence: tuple[ProjectionSignalEvidence, ...]
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FolderSignalVectorProjection:
    signal_id: str
    tenant: str
    folder_id: str
    signal_type: str
    signal_key: str
    source_version: str
    index_input_digest: str
    related_document_id: str | None
    attributes: Metadata
    confidence: float | None
    evidence: tuple[Metadata, ...]
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FolderVectorProjection:
    tenant: str
    folder_id: str
    source_version: str
    index_input_digest: str
    created_at: str
    updated_at: str
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
