from __future__ import annotations

from foldmind_ai_core.core.application.models.projection_commands import (
    InvalidateFolderSignalsCommand,
    ProjectDocumentCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
)
from foldmind_ai_core.core.application.ports.outbound.checker.source_freshness import (
    SourceFreshnessChecker,
)


async def is_current_document_index_projection(
    source_freshness: SourceFreshnessChecker,
    command: ProjectDocumentCommand,
) -> bool:
    document = command.document
    return await source_freshness.is_current_document_index_input_digest(
        tenant=document.tenant,
        document_id=document.document_id,
        document_index_input_digest=command.document_index.document_index_input_digest,
    )


async def is_current_document_signal_projection(
    source_freshness: SourceFreshnessChecker,
    command: ProjectDocumentCommand,
) -> bool:
    document = command.document
    return await source_freshness.is_current_document_signal_input_digest(
        tenant=document.tenant,
        document_id=document.document_id,
        document_signal_input_digest=(
            command.document_index.document_signal_input_digest
        ),
        signal_generation_version=command.document_index.signal_generation_version,
    )


async def is_current_document_folder_relation_projection(
    source_freshness: SourceFreshnessChecker,
    command: ProjectDocumentFolderRelationsCommand,
) -> bool:
    snapshot = command.folder_relation_snapshot
    return await source_freshness.is_current_document_folder_relation_snapshot(
        tenant=snapshot.tenant,
        document_id=snapshot.document_id,
        source_version=snapshot.source_version,
    )


async def is_current_folder_index_projection(
    source_freshness: SourceFreshnessChecker,
    command: ProjectFolderCommand,
    *,
    folder_index_input_digest: str,
) -> bool:
    folder = command.folder
    return await source_freshness.is_current_folder_index_input_digest(
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        folder_index_input_digest=folder_index_input_digest,
    )


async def is_current_folder_signal_projection(
    source_freshness: SourceFreshnessChecker,
    command: ProjectFolderSignalsCommand,
) -> bool:
    folder = command.folder
    return await source_freshness.is_current_folder_signal_input_digest(
        tenant=folder.tenant,
        folder_id=folder.folder_id,
        folder_signal_input_digest=command.folder_signal_input_digest,
    )


async def is_current_folder_signal_invalidation(
    source_freshness: SourceFreshnessChecker,
    command: InvalidateFolderSignalsCommand,
) -> bool:
    return await source_freshness.is_current_folder_signal_input_digest(
        tenant=command.tenant,
        folder_id=command.folder_id,
        folder_signal_input_digest=command.folder_signal_input_digest,
    )
