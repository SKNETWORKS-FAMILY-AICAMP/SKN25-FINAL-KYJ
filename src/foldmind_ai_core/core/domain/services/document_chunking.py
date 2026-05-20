from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.shared.canonical_json import json_digest
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(frozen=True, slots=True)
class DocumentChunkingConfig:
    chunking_version: str
    embedding_model: str
    embedding_version: str
    index_schema_version: str
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
            "embedding_model",
            "embedding_version",
            "index_schema_version",
        ):
            if not getattr(self, field_name).strip():
                raise InvalidInputError(f"{field_name} must not be blank.")


@dataclass(frozen=True, slots=True)
class DocumentChunker:
    config: DocumentChunkingConfig

    def chunk(self, document: SourceDocument) -> list[DocumentChunk]:
        index_input_digest = document_index_input_digest(
            document=document,
            config=self.config,
        )
        text = document.full_text
        step = self.config.chunk_size - self.config.chunk_overlap
        chunks: list[DocumentChunk] = []
        for index, start in enumerate(range(0, len(text), step)):
            end = min(len(text), start + self.config.chunk_size)
            raw_chunk_text = text[start:end]
            chunk_text = raw_chunk_text.strip()
            if not chunk_text:
                continue
            adjusted_start = start + (len(raw_chunk_text) - len(raw_chunk_text.lstrip()))
            adjusted_end = end - (len(raw_chunk_text) - len(raw_chunk_text.rstrip()))
            chunks.append(
                DocumentChunk(
                    tenant=document.tenant,
                    document_type=document.document_type,
                    document_id=document.document_id,
                    source_version=document.source_version,
                    index_input_digest=index_input_digest,
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                    chunk_id=_chunk_id(
                        tenant=document.tenant,
                        document_id=document.document_id,
                        index_input_digest=index_input_digest,
                        chunk_index=index,
                    ),
                    chunk_index=index,
                    chunking_version=self.config.chunking_version,
                    text=chunk_text,
                    text_hash=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                    start_offset=adjusted_start,
                    end_offset=adjusted_end,
                    embedding_model=self.config.embedding_model,
                    embedding_version=self.config.embedding_version,
                    index_schema_version=self.config.index_schema_version,
                    metadata=dict(document.metadata),
                )
            )
        return chunks


def _chunk_id(
    *,
    tenant: str,
    document_id: str,
    index_input_digest: str,
    chunk_index: int,
) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            (
                f"chunk:{tenant}:{document_id}:{index_input_digest}:"
                f"{chunk_index}"
            ),
        )
    )


def document_index_input_digest(
    *,
    document: SourceDocument,
    config: DocumentChunkingConfig,
) -> str:
    return json_digest(
        {
            "kind": "document_content_index",
            "content_digest": hashlib.sha256(
                document.full_text.encode("utf-8")
            ).hexdigest(),
            "chunking": {
                "version": config.chunking_version,
                "chunk_size": config.chunk_size,
                "chunk_overlap": config.chunk_overlap,
            },
            "embedding": {
                "model": config.embedding_model,
                "version": config.embedding_version,
            },
            "schema": {
                "index_schema_version": config.index_schema_version,
            },
        }
    )
