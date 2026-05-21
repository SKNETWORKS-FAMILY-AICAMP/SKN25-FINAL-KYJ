from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.commands.projection import (
    DeleteFolderProjectionCommand,
    InvalidateFolderSignalsCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
)
from foldmind_ai_core.core.application.ports.outbound.embedding import EmbeddingProvider
from foldmind_ai_core.core.application.ports.outbound.projection_ledger import (
    ProjectionLedger,
)
from foldmind_ai_core.core.application.ports.outbound.source_freshness import (
    SourceFreshnessChecker,
)
from foldmind_ai_core.core.application.ports.outbound.vector_store import (
    FolderVectorStore,
    SignalVectorStore,
)
from foldmind_ai_core.core.application.services.embedding_results import embed_many, embed_one
from foldmind_ai_core.core.application.services.vector_projection_spec import VectorProjectionSpec
from foldmind_ai_core.core.application.projections.factories import (
    folder_signal_vector_projection_from_signal,
    folder_vector_projection_from_source,
)


@dataclass(slots=True)
class ProjectFolderVectorUseCase:
    embeddings: EmbeddingProvider
    folder_vectors: FolderVectorStore
    projection_spec: VectorProjectionSpec
    projection_ledger: ProjectionLedger | None = None
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: ProjectFolderCommand) -> None:
        if not _is_current_folder_source(self.source_freshness, command):
            return
        projection = folder_vector_projection_from_source(
            command.folder,
            embedding_model=self.projection_spec.embedding_model,
            embedding_version=self.projection_spec.embedding_version,
            index_schema_version=self.projection_spec.index_schema_version,
        )
        vector = embed_one(self.embeddings, projection.embedding_input)
        write = self.folder_vectors.upsert_folder_vector(projection=projection, vector=vector)
        if self.projection_ledger is not None:
            self.projection_ledger.record_folder_vector_projected(
                projection=projection,
                write=write,
            )


@dataclass(slots=True)
class DeleteFolderVectorUseCase:
    folder_vectors: FolderVectorStore
    projection_ledger: ProjectionLedger | None = None

    def execute(self, command: DeleteFolderProjectionCommand) -> None:
        self.folder_vectors.delete_folder_vector(
            folder_id=command.folder_id,
        )
        if self.projection_ledger is not None:
            self.projection_ledger.delete_folder_vector_records(
                folder_id=command.folder_id,
            )


@dataclass(slots=True)
class ProjectFolderSignalVectorsUseCase:
    embeddings: EmbeddingProvider
    signal_vectors: SignalVectorStore
    projection_spec: VectorProjectionSpec
    projection_ledger: ProjectionLedger | None = None
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: ProjectFolderSignalsCommand) -> None:
        if not _is_current_folder_signal_input_digest(self.source_freshness, command):
            return
        projections = tuple(
            folder_signal_vector_projection_from_signal(
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
        writes = self.signal_vectors.replace_folder_signals(
            tenant=command.folder.tenant,
            folder_id=command.folder.folder_id,
            signals=projections,
            vectors=vectors,
        )
        if self.projection_ledger is not None:
            self.projection_ledger.delete_folder_signal_vector_records(
                folder_id=command.folder.folder_id,
            )
            self.projection_ledger.record_folder_signal_vectors_projected(
                projections=projections,
                writes=writes,
            )


@dataclass(slots=True)
class InvalidateFolderSignalVectorsUseCase:
    signal_vectors: SignalVectorStore
    projection_ledger: ProjectionLedger | None = None
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: InvalidateFolderSignalsCommand) -> None:
        if not _is_current_folder_signal_invalidation(self.source_freshness, command):
            return
        self.signal_vectors.delete_stale_folder_signals(
            folder_id=command.folder_id,
            current_folder_signal_input_digest=command.folder_signal_input_digest,
        )
        if self.projection_ledger is not None:
            self.projection_ledger.delete_stale_folder_signal_vector_records(
                folder_id=command.folder_id,
                current_source_input_digest=command.folder_signal_input_digest,
            )


@dataclass(slots=True)
class DeleteFolderSignalVectorsUseCase:
    signal_vectors: SignalVectorStore
    projection_ledger: ProjectionLedger | None = None

    def execute(self, command: DeleteFolderProjectionCommand) -> None:
        self.signal_vectors.delete_folder_signals(folder_id=command.folder_id)
        if self.projection_ledger is not None:
            self.projection_ledger.delete_folder_signal_vector_records(
                folder_id=command.folder_id,
            )


def _is_current_folder_source(
    source_freshness: SourceFreshnessChecker | None,
    command: ProjectFolderCommand,
) -> bool:
    if source_freshness is None:
        return True
    folder = command.folder
    return source_freshness.is_current_folder_source(
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        source_version=folder.source_version,
    )


def _is_current_folder_signal_input_digest(
    source_freshness: SourceFreshnessChecker | None,
    command: ProjectFolderSignalsCommand,
) -> bool:
    if source_freshness is None:
        return True
    folder = command.folder
    return source_freshness.is_current_folder_signal_input_digest(
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        folder_signal_input_digest=command.folder_signal_input_digest,
    )


def _is_current_folder_signal_invalidation(
    source_freshness: SourceFreshnessChecker | None,
    command: InvalidateFolderSignalsCommand,
) -> bool:
    if source_freshness is None:
        return True
    return source_freshness.is_current_folder_signal_input_digest(
        tenant=command.tenant,
        folder_id=command.folder_id,
        folder_signal_input_digest=command.folder_signal_input_digest,
    )
