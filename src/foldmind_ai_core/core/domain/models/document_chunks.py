from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(frozen=True, slots=True)
class DocumentChunkingPolicy:
    chunking_version: str
    search_text_policy_version: str = "simple-v1"
    chunk_size: int = 1200
    chunk_overlap: int = 120

    def __post_init__(self) -> None:
        if (
            isinstance(self.chunk_size, bool)
            or not isinstance(self.chunk_size, int)
            or self.chunk_size <= 0
        ):
            raise InvalidInputError("chunk_size must be a positive integer.")
        if (
            isinstance(self.chunk_overlap, bool)
            or not isinstance(self.chunk_overlap, int)
            or self.chunk_overlap < 0
        ):
            raise InvalidInputError("chunk_overlap must be a non-negative integer.")
        if self.chunk_overlap >= self.chunk_size:
            raise InvalidInputError("chunk_overlap must be less than chunk_size.")
        for field_name in (
            "chunking_version",
            "search_text_policy_version",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidInputError(f"{field_name} must not be blank.")


@dataclass(frozen=True, slots=True)
class DocumentIndexingPolicy:
    chunking: DocumentChunkingPolicy
    index_schema_version: str

    def __post_init__(self) -> None:
        for field_name in (
            "index_schema_version",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise InvalidInputError(f"{field_name} must not be blank.")


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    document_index_input_digest: str
    created_at: str
    updated_at: str
    chunk_id: str
    chunk_index: int
    text: str
    start_offset: int
    end_offset: int
    metadata: Metadata = field(default_factory=dict)
