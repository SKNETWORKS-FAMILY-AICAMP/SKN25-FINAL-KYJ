from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.commands.projection import (
    DeleteDocumentProjectionCommand,
    ProjectDocumentCommand,
)
from foldmind_ai_core.core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.core.application.ports.outbound.projection_ledger import (
    ProjectionLedger,
)
from foldmind_ai_core.core.application.ports.outbound.source_freshness import (
    SourceFreshnessChecker,
)
from foldmind_ai_core.core.application.ports.outbound.vector_store import (
    DocumentChunkVectorStore,
)
from foldmind_ai_core.core.application.services.embedding_results import embed_many


@dataclass(slots=True)
class ProjectDocumentChunkVectorsUseCase:
    embeddings: EmbeddingProvider
    chunk_vectors: DocumentChunkVectorStore
    projection_ledger: ProjectionLedger | None = None
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: ProjectDocumentCommand) -> None:
        if not _is_current_document_source(self.source_freshness, command):
            return
        if not command.chunks:
            writes = self.chunk_vectors.replace_document_chunks(
                tenant=command.document.tenant,
                document_id=command.document.document_id,
                chunks=(),
                vectors=(),
            )
            if self.projection_ledger is not None:
                self.projection_ledger.delete_chunk_vector_records(
                    document_id=command.document.document_id,
                )
                self.projection_ledger.record_chunk_vectors_projected(
                    projections=(),
                    writes=writes,
                )
            return
        vectors = embed_many(self.embeddings, [chunk.text for chunk in command.chunks])
        writes = self.chunk_vectors.replace_document_chunks(
            tenant=command.document.tenant,
            document_id=command.document.document_id,
            chunks=command.chunks,
            vectors=vectors,
        )
        if self.projection_ledger is not None:
            self.projection_ledger.delete_chunk_vector_records(
                document_id=command.document.document_id,
            )
            self.projection_ledger.record_chunk_vectors_projected(
                projections=command.chunks,
                writes=writes,
            )


@dataclass(slots=True)
class DeleteDocumentChunkVectorsUseCase:
    chunk_vectors: DocumentChunkVectorStore
    projection_ledger: ProjectionLedger | None = None

    def execute(self, command: DeleteDocumentProjectionCommand) -> None:
        self.chunk_vectors.delete_document_chunks(
            document_id=command.document_id,
        )
        if self.projection_ledger is not None:
            self.projection_ledger.delete_chunk_vector_records(
                document_id=command.document_id,
            )


def _is_current_document_source(
    source_freshness: SourceFreshnessChecker | None,
    command: ProjectDocumentCommand,
) -> bool:
    if source_freshness is None:
        return True
    document = command.document
    return source_freshness.is_current_document_source(
        tenant=document.tenant,
        document_id=document.document_id,
        source_version=document.source_version,
        content_digest=document.content_digest,
    )
