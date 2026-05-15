from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.agents.document_profiler_agent import DocumentProfilerAgent
from foldmind_ai_core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.application.services.document_chunker import DocumentChunker
from foldmind_ai_core.application.services.outbox_events import (
    document_deleted_event,
    document_indexed_event,
)
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.reference.documents import (
    SourceDocument,
)


@dataclass(slots=True)
class IndexDocumentUseCase:
    profiler: DocumentProfilerAgent
    indexing_uow: IndexingUnitOfWork
    chunker: DocumentChunker

    def execute(self, document: SourceDocument) -> list[DocumentChunk]:
        chunks = self.chunker.chunk(document)
        if not chunks:
            self._delete_document_profile_and_publish_event(document)
            return []

        profile = self.profiler.profile(document, chunks)
        event = document_indexed_event(
            document=document,
            chunks=tuple(chunks),
            profile=profile,
        )
        with self.indexing_uow.transaction() as tx:
            tx.upsert_document_profile(profile)
            tx.append_outbox_event(event)
        return chunks

    def _delete_document_profile_and_publish_event(self, document: SourceDocument) -> None:
        event = document_deleted_event(
            document_id=document.document_id,
        )
        with self.indexing_uow.transaction() as tx:
            tx.delete_document_profile(document_id=document.document_id)
            tx.append_outbox_event(event)
