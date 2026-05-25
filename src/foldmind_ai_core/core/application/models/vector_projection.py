from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.domain.models.document_signals import DocumentSignalEvidence
from foldmind_ai_core.shared.types import Metadata
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(frozen=True, slots=True)
class VectorWriteResult:
    collection_name: str
    point_id: str
    payload_digest: str


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
    metadata: Metadata = field(default_factory=dict)


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
    evidence: tuple[DocumentSignalEvidence, ...]
    embedding_input: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    extractor_name: str
    extractor_version: str
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
    extractor_name: str
    extractor_version: str
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
    parent_folder_id: str | None = None
    description: str = ""
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VectorProjectionSpec:
    embedding_model: str
    embedding_version: str
    index_schema_version: str

    def __post_init__(self) -> None:
        for field_name in (
            "embedding_model",
            "embedding_version",
            "index_schema_version",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidInputError(f"{field_name} must not be blank.")
