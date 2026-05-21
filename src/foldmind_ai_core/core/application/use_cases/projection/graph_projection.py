from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.commands.projection import (
    DeleteDocumentProjectionCommand,
    DeleteFolderProjectionCommand,
    InvalidateFolderSignalsCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectDocumentCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
)
from foldmind_ai_core.core.application.ports.outbound.graph_store import GraphStore
from foldmind_ai_core.core.application.ports.outbound.source_freshness import (
    SourceFreshnessChecker,
)
from foldmind_ai_core.core.application.projections.factories import (
    document_folder_relation_projection_from_snapshot,
    document_relationship_projection_from_source_document,
    document_signal_graph_projection_from_profile,
    folder_relationship_projection_from_source_folder,
    folder_signal_graph_projection_from_folder,
)


@dataclass(slots=True)
class ProjectDocumentGraphUseCase:
    graph: GraphStore
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: ProjectDocumentCommand) -> None:
        if not _is_current_document_source(self.source_freshness, command):
            return
        relationships = document_relationship_projection_from_source_document(
            command.document,
        )
        signals = document_signal_graph_projection_from_profile(
            command.profile,
            command.signals,
        )
        self.graph.replace_document_projection(
            relationships=relationships,
            signals=signals,
        )


@dataclass(slots=True)
class ProjectDocumentFolderRelationsGraphUseCase:
    graph: GraphStore
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: ProjectDocumentFolderRelationsCommand) -> None:
        if not _is_current_document_folder_relation_snapshot(
            self.source_freshness,
            command,
        ):
            return
        self.graph.replace_document_folder_relations(
            projection=document_folder_relation_projection_from_snapshot(
                command.folder_relation_snapshot
            )
        )


@dataclass(slots=True)
class DeleteDocumentGraphUseCase:
    graph: GraphStore

    def execute(self, command: DeleteDocumentProjectionCommand) -> None:
        self.graph.delete_document(
            document_id=command.document_id,
        )


@dataclass(slots=True)
class ProjectFolderGraphUseCase:
    graph: GraphStore
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: ProjectFolderCommand) -> None:
        if not _is_current_folder_source(self.source_freshness, command):
            return
        relationships = folder_relationship_projection_from_source_folder(command.folder)
        self.graph.replace_folder_projection(relationships=relationships)


@dataclass(slots=True)
class ProjectFolderSignalsGraphUseCase:
    graph: GraphStore
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: ProjectFolderSignalsCommand) -> None:
        if not _is_current_folder_signal_input_digest(self.source_freshness, command):
            return
        signals = folder_signal_graph_projection_from_folder(
            command.folder,
            command.signals,
            folder_signal_input_digest=command.folder_signal_input_digest,
            signal_generation_version=command.signal_generation_version,
        )
        self.graph.replace_folder_signals(signals=signals)


@dataclass(slots=True)
class InvalidateFolderSignalsGraphUseCase:
    graph: GraphStore
    source_freshness: SourceFreshnessChecker | None = None

    def execute(self, command: InvalidateFolderSignalsCommand) -> None:
        if not _is_current_folder_signal_invalidation(self.source_freshness, command):
            return
        self.graph.delete_stale_folder_signals(
            folder_id=command.folder_id,
            current_folder_signal_input_digest=command.folder_signal_input_digest,
        )


@dataclass(slots=True)
class DeleteFolderGraphUseCase:
    graph: GraphStore

    def execute(self, command: DeleteFolderProjectionCommand) -> None:
        self.graph.delete_folder(folder_id=command.folder_id)


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


def _is_current_document_folder_relation_snapshot(
    source_freshness: SourceFreshnessChecker | None,
    command: ProjectDocumentFolderRelationsCommand,
) -> bool:
    if source_freshness is None:
        return True
    snapshot = command.folder_relation_snapshot
    return source_freshness.is_current_document_folder_relation_snapshot(
        tenant=snapshot.tenant,
        document_id=snapshot.document_id,
        source_version=snapshot.source_version,
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
