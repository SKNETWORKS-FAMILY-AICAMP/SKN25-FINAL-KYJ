from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.models.projection_inputs import (
    ProjectionSignalEvidence,
)
from foldmind_ai_core.shared.types import Metadata
from foldmind_ai_core.shared.input_digest import input_digest


@dataclass(frozen=True, slots=True)
class VectorInput:
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    vector_schema_version: str

    @property
    def digest(self) -> str:
        return input_digest(
            "vector",
            {
                "embedding_input_hash": self.embedding_input_hash,
                "embedding_model": self.embedding_model,
                "embedding_version": self.embedding_version,
                "vector_schema_version": self.vector_schema_version,
            },
        )


@dataclass(frozen=True, slots=True)
class DocumentChunkVectorProjection:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    content_digest: str
    source_input_digest: str
    vector_input_digest: str
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
    source_input_digest: str
    vector_input_digest: str
    created_at: str
    updated_at: str
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    title: str = ""


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
    source_input_digest: str
    vector_input_digest: str
    signal_generation_version: str
    attributes: Metadata
    confidence: float | None
    evidence: tuple[ProjectionSignalEvidence, ...]
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    extractor_name: str = ""
    extractor_version: str = ""
    generation_model: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FolderSignalVectorProjection:
    signal_id: str
    tenant: str
    folder_id: str
    signal_type: str
    signal_key: str
    source_version: str
    source_input_digest: str
    vector_input_digest: str
    signal_generation_version: str
    related_document_id: str | None
    attributes: Metadata
    confidence: float | None
    evidence: tuple[Metadata, ...]
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    extractor_name: str = ""
    extractor_version: str = ""
    generation_model: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FolderVectorProjection:
    tenant: str
    folder_id: str
    source_version: str
    source_input_digest: str
    vector_input_digest: str
    created_at: str
    updated_at: str
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    name: str = ""
    path: str | None = None
    description: str = ""
