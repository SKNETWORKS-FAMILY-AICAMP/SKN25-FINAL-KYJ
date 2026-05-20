from __future__ import annotations

from foldmind_ai_core.adapters.inbound.messaging.message_codec import (
    document_deleted_event_from_outbox,
    document_folder_relations_indexed_event_from_outbox,
    document_indexed_event_from_outbox,
    folder_deleted_event_from_outbox,
    folder_indexed_event_from_outbox,
    folder_signals_indexed_event_from_outbox,
    folder_signals_invalidated_event_from_outbox,
)
from foldmind_ai_core.core.application.commands.projection import (
    DeleteDocumentProjectionCommand,
    DeleteFolderProjectionCommand,
    InvalidateFolderSignalsCommand,
    ProjectDocumentFolderRelationsCommand,
    ProjectDocumentCommand,
    ProjectFolderCommand,
    ProjectFolderSignalsCommand,
)
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent


def project_document_command(event: OutboxEvent) -> ProjectDocumentCommand:
    projection_event = document_indexed_event_from_outbox(event)
    return ProjectDocumentCommand(
        document=projection_event.document,
        chunks=projection_event.chunks,
        profile=projection_event.profile,
        signals=projection_event.signals,
    )


def project_document_folder_relations_command(
    event: OutboxEvent,
) -> ProjectDocumentFolderRelationsCommand:
    projection_event = document_folder_relations_indexed_event_from_outbox(event)
    return ProjectDocumentFolderRelationsCommand(
        folder_relation_snapshot=projection_event.folder_relation_snapshot,
    )


def delete_document_projection_command(
    event: OutboxEvent,
) -> DeleteDocumentProjectionCommand:
    projection_event = document_deleted_event_from_outbox(event)
    return DeleteDocumentProjectionCommand(
        document_id=projection_event.document_id,
        affected_folder_ids=projection_event.affected_folder_ids,
    )


def project_folder_command(event: OutboxEvent) -> ProjectFolderCommand:
    projection_event = folder_indexed_event_from_outbox(event)
    return ProjectFolderCommand(
        folder=projection_event.folder,
    )


def project_folder_signals_command(event: OutboxEvent) -> ProjectFolderSignalsCommand:
    projection_event = folder_signals_indexed_event_from_outbox(event)
    return ProjectFolderSignalsCommand(
        folder=projection_event.folder,
        folder_signal_input_revision=projection_event.folder_signal_input_revision,
        signals=projection_event.signals,
    )


def invalidate_folder_signals_command(event: OutboxEvent) -> InvalidateFolderSignalsCommand:
    projection_event = folder_signals_invalidated_event_from_outbox(event)
    return InvalidateFolderSignalsCommand(
        folder_id=projection_event.folder_id,
        folder_signal_input_revision=projection_event.folder_signal_input_revision,
    )


def delete_folder_projection_command(event: OutboxEvent) -> DeleteFolderProjectionCommand:
    projection_event = folder_deleted_event_from_outbox(event)
    return DeleteFolderProjectionCommand(
        folder_id=projection_event.folder_id,
    )
