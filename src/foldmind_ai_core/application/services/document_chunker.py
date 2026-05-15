from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.reference.documents import SourceDocument
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
        if self.chunk_size <= 0:
            raise InvalidInputError("chunk_size must be greater than 0.")
        if self.chunk_overlap < 0:
            raise InvalidInputError("chunk_overlap must be greater than or equal to 0.")
        if self.chunk_overlap >= self.chunk_size:
            raise InvalidInputError("chunk_overlap must be less than chunk_size.")
        if not self.chunking_version.strip():
            raise InvalidInputError("chunking_version must not be blank.")
        if not self.embedding_model.strip():
            raise InvalidInputError("embedding_model must not be blank.")
        if not self.embedding_version.strip():
            raise InvalidInputError("embedding_version must not be blank.")
        if not self.index_schema_version.strip():
            raise InvalidInputError("index_schema_version must not be blank.")


@dataclass(frozen=True, slots=True)
class DocumentChunker:
    config: DocumentChunkingConfig

    def chunk(self, document: SourceDocument) -> list[DocumentChunk]:
        text = document.full_text
        if not text:
            return []

        step = self.config.chunk_size - self.config.chunk_overlap
        chunks: list[DocumentChunk] = []
        for index, start in enumerate(range(0, len(text), step)):
            end = min(len(text), start + self.config.chunk_size)
            chunk_text = text[start:end].strip()
            if not chunk_text:
                continue
            chunks.append(
                DocumentChunk(
                    tenant=document.tenant,
                    document_type=document.document_type,
                    document_id=document.document_id,
                    source_version=document.source_version,
                    chunk_id=_chunk_id(
                        document_id=document.document_id,
                        source_version=document.source_version,
                        chunking_version=self.config.chunking_version,
                        chunk_index=index,
                    ),
                    chunk_index=index,
                    chunking_version=self.config.chunking_version,
                    text=chunk_text,
                    text_hash=_hash_text(chunk_text),
                    start_offset=start,
                    end_offset=end,
                    embedding_model=self.config.embedding_model,
                    embedding_version=self.config.embedding_version,
                    index_schema_version=self.config.index_schema_version,
                    metadata=dict(document.metadata),
                )
            )
        return chunks


def _chunk_id(
    *,
    document_id: str,
    source_version: str,
    chunking_version: str,
    chunk_index: int,
) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"chunk:{document_id}:{source_version}:{chunking_version}:{chunk_index}",
        )
    )


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
