from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.ports.document_keyword_store import DocumentKeywordSearchStore
from ai_core.application.ports.document_vector_store import DocumentVectorStore
from ai_core.application.ports.embedding import EmbeddingProvider
from ai_core.domain.chunks import DocumentChunk
from ai_core.domain.documents import SourceDocument


@dataclass(slots=True)
class IndexDocumentUseCase:
    embeddings: EmbeddingProvider
    documents: DocumentVectorStore
    keywords: DocumentKeywordSearchStore | None = None
    chunk_size: int = 1200
    chunk_overlap: int = 120

    def execute(self, document: SourceDocument) -> list[DocumentChunk]:
        chunks = self._chunk(document)
        if not chunks:
            self.documents.delete(
                tenant=document.tenant,
                entity_type=document.entity_type,
                entity_id=document.entity_id,
            )
            if self.keywords is not None:
                self.keywords.delete(
                    tenant=document.tenant,
                    entity_type=document.entity_type,
                    entity_id=document.entity_id,
                )
            return []

        vectors = self.embeddings.embed_texts([chunk.text for chunk in chunks])
        self.documents.upsert(chunks, vectors)
        if self.keywords is not None:
            self.keywords.upsert(chunks)
        return chunks

    def _chunk(self, document: SourceDocument) -> list[DocumentChunk]:
        text = document.full_text
        if not text:
            return []

        step = max(1, self.chunk_size - self.chunk_overlap)
        chunks: list[DocumentChunk] = []
        for index, start in enumerate(range(0, len(text), step)):
            end = min(len(text), start + self.chunk_size)
            chunk_text = text[start:end].strip()
            if not chunk_text:
                continue
            chunks.append(
                DocumentChunk(
                    tenant=document.tenant,
                    entity_type=document.entity_type,
                    entity_id=document.entity_id,
                    version=document.version,
                    chunk_id=f"{document.source_key}:chunk:{index}",
                    text=chunk_text,
                    chunk_index=index,
                    start_offset=start,
                    end_offset=end,
                    folder_ids=document.folder_ids,
                    tags=document.tags,
                    metadata=dict(document.metadata),
                )
            )
        return chunks
