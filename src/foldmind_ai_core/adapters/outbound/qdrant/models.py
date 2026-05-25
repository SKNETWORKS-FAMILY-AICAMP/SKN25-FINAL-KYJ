from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import JsonObject


@dataclass(frozen=True, slots=True)
class QdrantDocumentChunkPayload:
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
    search_text: str
    chunk_index: int
    source_start_offset: int
    source_end_offset: int
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class QdrantDocumentPayload:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    content_digest: str
    source_input_digest: str
    vector_input_digest: str
    created_at: str
    updated_at: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    title: str = ""
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class QdrantSignalPayload:
    signal_id: str
    tenant: str
    owner_kind: str
    document_type: str | None
    document_id: str | None
    folder_id: str | None
    signal_type: str
    signal_key: str
    text: str
    source_version: str
    content_digest: str | None
    source_input_digest: str
    vector_input_digest: str
    signal_generation_version: str
    related_document_id: str | None
    attributes: JsonObject
    evidence: tuple[JsonObject, ...]
    confidence: float | None
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    extractor_name: str
    extractor_version: str
    generation_model: str | None = None
    metadata: JsonObject = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class QdrantFolderPayload:
    tenant: str
    folder_id: str
    source_version: str
    source_input_digest: str
    vector_input_digest: str
    created_at: str
    updated_at: str
    embedding_input_hash: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    name: str = ""
    path: str | None = None
    parent_folder_id: str | None = None
    description: str = ""
    metadata: JsonObject = field(default_factory=dict)
