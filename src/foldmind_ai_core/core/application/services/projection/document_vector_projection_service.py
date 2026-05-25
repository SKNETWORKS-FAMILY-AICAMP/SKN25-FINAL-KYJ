from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from foldmind_ai_core.core.application.models.projection_commands import (
    DeleteDocumentProjectionCommand,
    ProjectDocumentCommand,
)
from foldmind_ai_core.core.application.embedding_results import embed_many, embed_one
from foldmind_ai_core.core.application.execution.blocking_io import run_blocking
from foldmind_ai_core.core.application.ports.outbound.checker.source_freshness import (
    SourceFreshnessChecker,
)
from foldmind_ai_core.core.application.ports.outbound.provider.embedding import EmbeddingProvider
from foldmind_ai_core.core.application.ports.outbound.session.projection_ledger_session import (
    ProjectionLedgerSessionProvider,
)
from foldmind_ai_core.core.application.ports.outbound.store.vector_store import (
    DocumentChunkVectorStore,
    DocumentVectorStore,
    SignalVectorStore,
)
from foldmind_ai_core.core.application.mappers.projection import (
    document_vector_projection_from_index_record,
    signal_vector_projection_from_signal,
)
from foldmind_ai_core.core.application.services.projection.freshness import (
    is_current_document_index_projection,
    is_current_document_signal_projection,
)
from foldmind_ai_core.core.application.mappers.projection_ledger import (
    chunk_vector_projection_state,
    document_signal_vector_projection_state,
    document_vector_projection_record,
)
from foldmind_ai_core.core.application.models.vector_projection import (
    DocumentChunkVectorProjection,
    VectorWriteResult,
)
from foldmind_ai_core.core.application.models.vector_projection import VectorProjectionSpec

T = TypeVar("T")


@dataclass(slots=True)
class DocumentVectorProjectionService:
    embeddings: EmbeddingProvider
    chunk_vectors: DocumentChunkVectorStore | None
    document_vectors: DocumentVectorStore | None
    signal_vectors: SignalVectorStore | None
    projection_spec: VectorProjectionSpec | None
    source_freshness: SourceFreshnessChecker
    projection_ledger: ProjectionLedgerSessionProvider

    async def project_document_chunks(self, command: ProjectDocumentCommand) -> None:
        chunk_vectors = _required(self.chunk_vectors, "Document chunk vector store")
        if not await is_current_document_index_projection(self.source_freshness, command):
            return
        if not command.chunks:
            writes = await run_blocking(
                chunk_vectors.replace_document_chunks,
                tenant=command.document.tenant,
                document_id=command.document.document_id,
                chunks=(),
                vectors=(),
            )
            await _record_chunk_vectors(
                self.projection_ledger,
                tenant=command.document.tenant,
                document_id=command.document.document_id,
                projections=(),
                writes=writes,
            )
            return
        vectors = await run_blocking(
            embed_many,
            self.embeddings,
            [chunk.text for chunk in command.chunks],
        )
        writes = await run_blocking(
            chunk_vectors.replace_document_chunks,
            tenant=command.document.tenant,
            document_id=command.document.document_id,
            chunks=command.chunks,
            vectors=vectors,
        )
        await _record_chunk_vectors(
            self.projection_ledger,
            tenant=command.document.tenant,
            document_id=command.document.document_id,
            projections=command.chunks,
            writes=writes,
        )

    async def delete_document_chunks(
        self,
        command: DeleteDocumentProjectionCommand,
    ) -> None:
        chunk_vectors = _required(self.chunk_vectors, "Document chunk vector store")
        await run_blocking(
            chunk_vectors.delete_document_chunks,
            tenant=command.tenant,
            document_id=command.document_id,
        )
        async with self.projection_ledger.transaction() as session:
            await session.projection_ledger.delete_chunk_vector_records(
                tenant=command.tenant,
                document_id=command.document_id,
            )

    async def project_document_vector(self, command: ProjectDocumentCommand) -> None:
        document_vectors = _required(self.document_vectors, "Document vector store")
        projection_spec = _required(self.projection_spec, "Vector projection spec")
        if not await is_current_document_signal_projection(self.source_freshness, command):
            return
        projection = document_vector_projection_from_index_record(
            command.document,
            command.document_index,
            command.signals,
            embedding_model=projection_spec.embedding_model,
            embedding_version=projection_spec.embedding_version,
            index_schema_version=projection_spec.index_schema_version,
        )
        vector = await run_blocking(embed_one, self.embeddings, projection.embedding_input)
        write = await run_blocking(
            document_vectors.upsert_document_vector,
            projection=projection,
            vector=vector,
        )
        async with self.projection_ledger.transaction() as session:
            await session.projection_ledger.record_document_vector_projected(
                record=document_vector_projection_record(projection, write),
            )

    async def delete_document_vector(
        self,
        command: DeleteDocumentProjectionCommand,
    ) -> None:
        document_vectors = _required(self.document_vectors, "Document vector store")
        await run_blocking(
            document_vectors.delete_document_vector,
            tenant=command.tenant,
            document_id=command.document_id,
        )
        async with self.projection_ledger.transaction() as session:
            await session.projection_ledger.delete_document_vector_records(
                tenant=command.tenant,
                document_id=command.document_id,
            )

    async def project_document_signals(self, command: ProjectDocumentCommand) -> None:
        signal_vectors = _required(self.signal_vectors, "Signal vector store")
        projection_spec = _required(self.projection_spec, "Vector projection spec")
        if not await is_current_document_signal_projection(self.source_freshness, command):
            return
        projections = tuple(
            signal_vector_projection_from_signal(
                signal,
                content_digest=command.document.content_digest,
                embedding_model=projection_spec.embedding_model,
                embedding_version=projection_spec.embedding_version,
                index_schema_version=projection_spec.index_schema_version,
            )
            for signal in command.signals
        )
        vectors = await run_blocking(
            embed_many,
            self.embeddings,
            tuple(projection.embedding_input for projection in projections),
        )
        writes = await run_blocking(
            signal_vectors.replace_document_signals,
            tenant=command.document.tenant,
            document_id=command.document.document_id,
            signals=projections,
            vectors=vectors,
        )
        async with self.projection_ledger.transaction() as session:
            await session.projection_ledger.replace_signal_vector_records(
                tenant=command.document.tenant,
                document_id=command.document.document_id,
                records=document_signal_vector_projection_state(
                    projections,
                    writes,
                ),
            )

    async def delete_document_signals(
        self,
        command: DeleteDocumentProjectionCommand,
    ) -> None:
        signal_vectors = _required(self.signal_vectors, "Signal vector store")
        await run_blocking(
            signal_vectors.delete_document_signals,
            tenant=command.tenant,
            document_id=command.document_id,
        )
        async with self.projection_ledger.transaction() as session:
            await session.projection_ledger.delete_signal_vector_records(
                tenant=command.tenant,
                document_id=command.document_id,
            )


async def _record_chunk_vectors(
    projection_ledger: ProjectionLedgerSessionProvider,
    *,
    tenant: str,
    document_id: str,
    projections: tuple[DocumentChunkVectorProjection, ...],
    writes: tuple[VectorWriteResult, ...],
) -> None:
    async with projection_ledger.transaction() as session:
        await session.projection_ledger.replace_chunk_vector_records(
            tenant=tenant,
            document_id=document_id,
            records=chunk_vector_projection_state(projections, writes),
        )


def _required(value: T | None, name: str) -> T:
    if value is None:
        raise RuntimeError(f"{name} is required.")
    return value
