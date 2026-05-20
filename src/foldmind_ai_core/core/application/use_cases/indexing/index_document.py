from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.capabilities.profiling import DocumentSignalExtractor
from foldmind_ai_core.core.application.commands.indexing import IndexDocumentCommand
from foldmind_ai_core.core.application.factories.source_snapshots import (
    source_document_from_index_command,
)
from foldmind_ai_core.core.application.ports.outbound.indexing_unit_of_work import (
    IndexingUnitOfWork,
)
from foldmind_ai_core.core.application.results.indexing import IndexDocumentResult
from foldmind_ai_core.core.domain.services.document_chunking import DocumentChunker
from foldmind_ai_core.core.application.services.outbox_events import (
    document_deleted_event,
    document_indexed_event,
)


@dataclass(slots=True)
class IndexDocumentUseCase:
    signal_extractor: DocumentSignalExtractor
    indexing_uow: IndexingUnitOfWork
    chunker: DocumentChunker

    def execute(self, command: IndexDocumentCommand) -> IndexDocumentResult:
        document = source_document_from_index_command(command)
        chunks = self.chunker.chunk(document)
        if not chunks:
            with self.indexing_uow.transaction() as tx:
                deleted = tx.mark_document_deleted(
                    document_id=document.document_id,
                )
                event_tenant = deleted.tenant if deleted is not None else document.tenant
                affected_folder_ids = (
                    deleted.affected_folder_ids if deleted is not None else ()
                )
                tx.append_outbox_event(
                    document_deleted_event(
                        tenant=event_tenant,
                        document_id=document.document_id,
                        affected_folder_ids=affected_folder_ids,
                    )
                )
            return IndexDocumentResult(indexed_chunk_count=0)

        extraction = self.signal_extractor.profile(document, chunks)
        event = document_indexed_event(
            document=document,
            chunks=tuple(chunks),
            profile=extraction.profile,
            signals=extraction.signals,
        )
        with self.indexing_uow.transaction() as tx:
            tx.upsert_document_index(
                document=document,
                chunks=tuple(chunks),
                profile=extraction.profile,
                signals=extraction.signals,
            )
            tx.append_outbox_event(event)
        return IndexDocumentResult(indexed_chunk_count=len(chunks))
