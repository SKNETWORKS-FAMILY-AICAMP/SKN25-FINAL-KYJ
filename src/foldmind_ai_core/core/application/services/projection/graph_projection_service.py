from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.models.projection_commands import (
    DeleteDocumentProjectionCommand,
    DeleteFolderProjectionCommand,
    InvalidateFolderSignalsCommand,
    ProjectDocumentCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
)
from foldmind_ai_core.core.application.execution.blocking_io import run_blocking
from foldmind_ai_core.core.application.ports.outbound.checker.source_freshness import (
    SourceFreshnessChecker,
)
from foldmind_ai_core.core.application.ports.outbound.store.graph_store import GraphStore
from foldmind_ai_core.core.application.services.projection.freshness import (
    is_current_document_folder_relation_projection,
    is_current_document_signal_projection,
    is_current_folder_index_projection,
    is_current_folder_signal_invalidation,
    is_current_folder_signal_projection,
)
from foldmind_ai_core.core.domain.services.folder_projection_digest_service import (
    FolderProjectionDigestService,
)


@dataclass(slots=True)
class GraphProjectionService:
    graph: GraphStore
    source_freshness: SourceFreshnessChecker
    folder_projection_digest: FolderProjectionDigestService = field(
        default_factory=FolderProjectionDigestService,
    )

    async def project_document_graph(self, command: ProjectDocumentCommand) -> None:
        if not await is_current_document_signal_projection(self.source_freshness, command):
            return
        await run_blocking(
            self.graph.replace_document_projection,
            document=command.document,
            document_index=command.document_index,
            signals=command.signals,
        )

    async def project_document_folder_relations(
        self,
        command: ProjectDocumentFolderRelationsCommand,
    ) -> None:
        if not await is_current_document_folder_relation_projection(
            self.source_freshness,
            command,
        ):
            return
        await run_blocking(
            self.graph.replace_document_folder_relations,
            projection=command.folder_relation_snapshot,
        )

    async def delete_document_graph(
        self,
        command: DeleteDocumentProjectionCommand,
    ) -> None:
        await run_blocking(
            self.graph.delete_document,
            tenant=command.tenant,
            document_id=command.document_id,
        )

    async def project_folder_graph(self, command: ProjectFolderCommand) -> None:
        folder_index_input_digest = self.folder_projection_digest.folder_index_input_digest(
            folder_id=command.folder.folder_id,
            folder=command.folder,
        )
        if not await is_current_folder_index_projection(
            self.source_freshness,
            command,
            folder_index_input_digest=folder_index_input_digest,
        ):
            return
        await run_blocking(
            self.graph.replace_folder_projection,
            folder=command.folder,
        )

    async def project_folder_signals(
        self,
        command: ProjectFolderSignalsCommand,
    ) -> None:
        if not await is_current_folder_signal_projection(
            self.source_freshness,
            command,
        ):
            return
        await run_blocking(
            self.graph.replace_folder_signals,
            folder=command.folder,
            folder_signal_input_digest=command.folder_signal_input_digest,
            signal_generation_version=command.signal_generation_version,
            signals=command.signals,
        )

    async def invalidate_folder_signals(
        self,
        command: InvalidateFolderSignalsCommand,
    ) -> None:
        if not await is_current_folder_signal_invalidation(
            self.source_freshness,
            command,
        ):
            return
        await run_blocking(
            self.graph.delete_stale_folder_signals,
            tenant=command.tenant,
            folder_id=command.folder_id,
            current_folder_signal_input_digest=command.folder_signal_input_digest,
        )

    async def delete_folder_graph(
        self,
        command: DeleteFolderProjectionCommand,
    ) -> None:
        await run_blocking(
            self.graph.delete_folder,
            tenant=command.tenant,
            folder_id=command.folder_id,
        )
