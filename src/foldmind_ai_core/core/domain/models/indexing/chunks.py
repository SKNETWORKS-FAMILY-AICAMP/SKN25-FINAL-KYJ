from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
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
