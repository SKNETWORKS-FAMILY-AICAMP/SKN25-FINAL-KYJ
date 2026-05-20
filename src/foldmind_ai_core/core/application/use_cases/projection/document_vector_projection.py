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
    DocumentVectorStore,
    SignalVectorStore,
)
from foldmind_ai_core.core.application.services.embedding_results import embed_many, embed_one
from foldmind_ai_core.core.application.services.vector_projection_spec import VectorProjectionSpec
from foldmind_ai_core.core.application.projections.factories import (
    document_vector_projection_from_profile,
    signal_vector_projection_from_signal,
)


@dataclass(slots=True)
class ProjectDocumentVectorUseCase:
    embeddings: EmbeddingProvider
    document_vectors: DocumentVectorStore
    projection_spec: VectorProjectionSpec
    projection_ledger: ProjectionLedger | None = None
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: ProjectDocumentCommand) -> None:
        if not _is_current_document_source(self.source_freshness, command):
            return
        projection = document_vector_projection_from_profile(
            command.profile,
            command.signals,
            embedding_model=self.projection_spec.embedding_model,
            embedding_version=self.projection_spec.embedding_version,
            index_schema_version=self.projection_spec.index_schema_version,
        )
        vector = embed_one(self.embeddings, projection.embedding_input)
        write = self.document_vectors.upsert_document_vector(
            projection=projection,
            vector=vector,
        )
        if self.projection_ledger is not None:
            self.projection_ledger.record_document_vector_projected(
                projection=projection,
                write=write,
            )


@dataclass(slots=True)
class DeleteDocumentVectorUseCase:
    document_vectors: DocumentVectorStore
    projection_ledger: ProjectionLedger | None = None

    def execute(self, command: DeleteDocumentProjectionCommand) -> None:
        self.document_vectors.delete_document_vector(
            document_id=command.document_id,
        )
        if self.projection_ledger is not None:
            self.projection_ledger.delete_document_vector_records(
                document_id=command.document_id,
            )


@dataclass(slots=True)
class ProjectDocumentSignalVectorsUseCase:
    embeddings: EmbeddingProvider
    signal_vectors: SignalVectorStore
    projection_spec: VectorProjectionSpec
    projection_ledger: ProjectionLedger | None = None
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: ProjectDocumentCommand) -> None:
        if not _is_current_document_source(self.source_freshness, command):
            return
        projections = tuple(
            signal_vector_projection_from_signal(
                signal,
                embedding_model=self.projection_spec.embedding_model,
                embedding_version=self.projection_spec.embedding_version,
                index_schema_version=self.projection_spec.index_schema_version,
            )
            for signal in command.signals
        )
        vectors = embed_many(
            self.embeddings,
            tuple(projection.embedding_input for projection in projections),
        )
        writes = self.signal_vectors.replace_document_signals(
            tenant=command.document.tenant,
            document_id=command.document.document_id,
            signals=projections,
            vectors=vectors,
        )
        if self.projection_ledger is not None:
            self.projection_ledger.delete_signal_vector_records(
                document_id=command.document.document_id,
            )
            self.projection_ledger.record_signal_vectors_projected(
                projections=projections,
                writes=writes,
            )


@dataclass(slots=True)
class DeleteDocumentSignalVectorsUseCase:
    signal_vectors: SignalVectorStore
    projection_ledger: ProjectionLedger | None = None

    def execute(self, command: DeleteDocumentProjectionCommand) -> None:
        self.signal_vectors.delete_document_signals(
            document_id=command.document_id,
        )
        if self.projection_ledger is not None:
            self.projection_ledger.delete_signal_vector_records(
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
