from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

from foldmind_ai_core.core.application.models.projection_commands import (
    DeleteFolderProjectionCommand,
    InvalidateFolderSignalsCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
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
    FolderVectorStore,
    SignalVectorStore,
)
from foldmind_ai_core.core.application.mappers.projection import (
    folder_signal_vector_projection_from_signal,
    folder_vector_projection_from_source,
)
from foldmind_ai_core.core.application.services.projection.freshness import (
    is_current_folder_index_projection,
    is_current_folder_signal_invalidation,
    is_current_folder_signal_projection,
)
from foldmind_ai_core.core.application.mappers.projection_ledger import (
    folder_signal_vector_projection_state,
    folder_vector_projection_record,
)
from foldmind_ai_core.core.application.models.vector_projection import VectorProjectionSpec

T = TypeVar("T")


@dataclass(slots=True)
class FolderVectorProjectionService:
    embeddings: EmbeddingProvider
    folder_vectors: FolderVectorStore | None
    signal_vectors: SignalVectorStore | None
    projection_spec: VectorProjectionSpec | None
    source_freshness: SourceFreshnessChecker
    projection_ledger: ProjectionLedgerSessionProvider

    async def project_folder_vector(self, command: ProjectFolderCommand) -> None:
        folder_vectors = _required(self.folder_vectors, "Folder vector store")
        projection_spec = _required(self.projection_spec, "Vector projection spec")
        projection = folder_vector_projection_from_source(
            command.folder,
            embedding_model=projection_spec.embedding_model,
            embedding_version=projection_spec.embedding_version,
            index_schema_version=projection_spec.index_schema_version,
        )
        if not await is_current_folder_index_projection(
            self.source_freshness,
            command,
            folder_index_input_digest=projection.source_input_digest,
        ):
            return
        vector = await run_blocking(embed_one, self.embeddings, projection.embedding_input)
        write = await run_blocking(
            folder_vectors.upsert_folder_vector,
            projection=projection,
            vector=vector,
        )
        async with self.projection_ledger.transaction() as session:
            await session.projection_ledger.record_folder_vector_projected(
                record=folder_vector_projection_record(projection, write),
            )

    async def delete_folder_vector(self, command: DeleteFolderProjectionCommand) -> None:
        folder_vectors = _required(self.folder_vectors, "Folder vector store")
        await run_blocking(
            folder_vectors.delete_folder_vector,
            tenant=command.tenant,
            folder_id=command.folder_id,
        )
        async with self.projection_ledger.transaction() as session:
            await session.projection_ledger.delete_folder_vector_records(
                tenant=command.tenant,
                folder_id=command.folder_id,
            )

    async def project_folder_signals(
        self,
        command: ProjectFolderSignalsCommand,
    ) -> None:
        signal_vectors = _required(self.signal_vectors, "Signal vector store")
        projection_spec = _required(self.projection_spec, "Vector projection spec")
        if not await is_current_folder_signal_projection(
            self.source_freshness,
            command,
        ):
            return
        projections = tuple(
            folder_signal_vector_projection_from_signal(
                signal,
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
            signal_vectors.replace_folder_signals,
            tenant=command.folder.tenant,
            folder_id=command.folder.folder_id,
            signals=projections,
            vectors=vectors,
        )
        async with self.projection_ledger.transaction() as session:
            await session.projection_ledger.replace_folder_signal_vector_records(
                tenant=command.folder.tenant,
                folder_id=command.folder.folder_id,
                records=folder_signal_vector_projection_state(projections, writes),
            )

    async def invalidate_folder_signals(
        self,
        command: InvalidateFolderSignalsCommand,
    ) -> None:
        signal_vectors = _required(self.signal_vectors, "Signal vector store")
        if not await is_current_folder_signal_invalidation(
            self.source_freshness,
            command,
        ):
            return
        await run_blocking(
            signal_vectors.delete_stale_folder_signals,
            tenant=command.tenant,
            folder_id=command.folder_id,
            current_folder_signal_input_digest=command.folder_signal_input_digest,
        )
        async with self.projection_ledger.transaction() as session:
            await session.projection_ledger.delete_stale_folder_signal_vector_records(
                tenant=command.tenant,
                folder_id=command.folder_id,
                current_source_input_digest=command.folder_signal_input_digest,
            )

    async def delete_folder_signals(
        self,
        command: DeleteFolderProjectionCommand,
    ) -> None:
        signal_vectors = _required(self.signal_vectors, "Signal vector store")
        await run_blocking(
            signal_vectors.delete_folder_signals,
            tenant=command.tenant,
            folder_id=command.folder_id,
        )
        async with self.projection_ledger.transaction() as session:
            await session.projection_ledger.delete_folder_signal_vector_records(
                tenant=command.tenant,
                folder_id=command.folder_id,
            )


def _required(value: T | None, name: str) -> T:
    if value is None:
        raise RuntimeError(f"{name} is required.")
    return value
