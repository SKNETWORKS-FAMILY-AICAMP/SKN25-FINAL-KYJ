from __future__ import annotations

import uuid
from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.document_chunks import (
    DocumentChunk,
    DocumentIndexingPolicy,
)
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.shared.input_digest import input_digest


@dataclass(frozen=True, slots=True)
class DocumentChunker:
    policy: DocumentIndexingPolicy

    def chunk(self, document: SourceDocument) -> list[DocumentChunk]:
        document_index_input_digest_value = self.index_input_digest(document)
        text = document.full_text
        step = self.policy.chunking.chunk_size - self.policy.chunking.chunk_overlap
        chunks: list[DocumentChunk] = []
        for index, start in enumerate(range(0, len(text), step)):
            end = min(len(text), start + self.policy.chunking.chunk_size)
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
                    document_index_input_digest=document_index_input_digest_value,
                    created_at=document.created_at,
                    updated_at=document.updated_at,
                    chunk_id=self._chunk_id(
                        tenant=document.tenant,
                        document_id=document.document_id,
                        document_index_input_digest=document_index_input_digest_value,
                        chunk_index=index,
                    ),
                    chunk_index=index,
                    text=chunk_text,
                    start_offset=adjusted_start,
                    end_offset=adjusted_end,
                    metadata=dict(document.metadata),
                )
            )
        return chunks

    def index_input_digest(self, document: SourceDocument) -> str:
        return input_digest(
            "document_index",
            {
                "content_digest": document.content_digest,
                "chunking": {
                    "version": self.policy.chunking.chunking_version,
                    "chunk_size": self.policy.chunking.chunk_size,
                    "chunk_overlap": self.policy.chunking.chunk_overlap,
                },
                "search_text_policy_version": (
                    self.policy.chunking.search_text_policy_version
                ),
                "index_schema_version": self.policy.index_schema_version,
            },
        )

    @staticmethod
    def _chunk_id(
        *,
        tenant: str,
        document_id: str,
        document_index_input_digest: str,
        chunk_index: int,
    ) -> str:
        return str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                (
                    f"chunk:{tenant}:{document_id}:{document_index_input_digest}:"
                    f"{chunk_index}"
                ),
            )
        )
