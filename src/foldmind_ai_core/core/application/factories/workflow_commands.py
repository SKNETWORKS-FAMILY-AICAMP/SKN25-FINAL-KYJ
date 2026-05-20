from __future__ import annotations

from foldmind_ai_core.core.application.commands.workflow import (
    CreateDocumentOutputCommand,
    CreateFolderOutputCommand,
    HostActionOutputCommand,
    HostActionResultCommand,
    LinkDocumentsOutputCommand,
    MoveDocumentOutputCommand,
    TaskRequestContextCommand,
    UpdateDocumentOutputCommand,
)
from foldmind_ai_core.core.domain.models.workflow.actions import (
    CreateDocumentOutput,
    CreateFolderOutput,
    HostActionOutput,
    HostActionResult,
    HostActionResultType,
    HostActionType,
    LinkDocumentsOutput,
    MoveDocumentOutput,
    UpdateDocumentOutput,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskContext


def task_context_from_command(context: TaskRequestContextCommand) -> TaskContext:
    return TaskContext(
        requested_at=context.requested_at,
        document_id=context.document_id,
        folder_id=context.folder_id,
    )


def host_action_result_from_command(result: HostActionResultCommand) -> HostActionResult:
    return HostActionResult(
        action_id=result.action_id,
        outcome=HostActionResultType(result.outcome),
        action_type=HostActionType(result.action_type) if result.action_type else None,
        output=host_action_output_from_command(result.output),
        error=result.error,
        metadata=dict(result.metadata),
    )


def host_action_output_from_command(
    output: HostActionOutputCommand | None,
) -> HostActionOutput | None:
    if output is None:
        return None
    if isinstance(output, CreateFolderOutputCommand):
        return CreateFolderOutput(
            folder_id=output.folder_id,
            name=output.name,
            parent_folder_id=output.parent_folder_id,
        )
    if isinstance(output, CreateDocumentOutputCommand):
        return CreateDocumentOutput(
            created_document_id=output.created_document_id,
            created_document_type=output.created_document_type,
            source_version=output.source_version,
            folder_id=output.folder_id,
        )
    if isinstance(output, UpdateDocumentOutputCommand):
        return UpdateDocumentOutput(
            updated_document_type=output.updated_document_type,
            updated_document_id=output.updated_document_id,
            source_version=output.source_version,
        )
    if isinstance(output, MoveDocumentOutputCommand):
        return MoveDocumentOutput(
            moved_document_type=output.moved_document_type,
            moved_document_id=output.moved_document_id,
            target_folder_id=output.target_folder_id,
            source_folder_id=output.source_folder_id,
        )
    if isinstance(output, LinkDocumentsOutputCommand):
        return LinkDocumentsOutput(
            source_type=output.source_type,
            source_id=output.source_id,
            target_type=output.target_type,
            target_id=output.target_id,
            relationship=output.relationship,
            link_id=output.link_id,
        )
    raise TypeError(f"Unsupported host action output command: {type(output).__name__}")
