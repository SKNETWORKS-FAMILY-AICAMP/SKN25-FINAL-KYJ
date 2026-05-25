from __future__ import annotations

from typing import cast

from foldmind_ai_core.adapters.inbound.http.dtos.actions import (
    ActionPlanDTO,
    CreateDocumentInputDTO,
    CreateDocumentOutputDTO,
    CreateFolderInputDTO,
    CreateFolderOutputDTO,
    HostActionDTO,
    HostActionInputDTO,
    HostActionPolicyDTO,
    HostActionResultDTO,
    HostActionStatusDTO,
    HostActionTypeDTO,
    LinkDocumentsInputDTO,
    LinkDocumentsOutputDTO,
    MoveDocumentInputDTO,
    MoveDocumentOutputDTO,
    RecordHostActionResultRequest,
    UpdateDocumentInputDTO,
    UpdateDocumentOutputDTO,
)
from foldmind_ai_core.core.application.models.task_commands import (
    RecordActionResultCommand,
)
from foldmind_ai_core.core.domain.models.host_actions import (
    ActionPlan,
    CreateDocumentInput,
    CreateDocumentOutput,
    CreateFolderInput,
    CreateFolderOutput,
    HostAction,
    HostActionInput,
    HostActionOutput,
    HostActionPolicy,
    HostActionResult,
    HostActionResultType,
    HostActionType,
    LinkDocumentsInput,
    LinkDocumentsOutput,
    MoveDocumentInput,
    MoveDocumentOutput,
    UpdateDocumentInput,
    UpdateDocumentOutput,
)
from foldmind_ai_core.shared.validation import (
    require_non_blank,
    require_optional_non_blank,
    require_optional_uuid,
    require_uuid,
)

HostActionOutputDTO = (
    CreateFolderOutputDTO
    | CreateDocumentOutputDTO
    | UpdateDocumentOutputDTO
    | MoveDocumentOutputDTO
    | LinkDocumentsOutputDTO
)


def create_folder_input_dto_from_domain(
    action_input: CreateFolderInput,
) -> CreateFolderInputDTO:
    return CreateFolderInputDTO(
        name=action_input.name,
        parent_folder_id=action_input.parent_folder_id,
        metadata=dict(action_input.metadata),
    )


def create_document_input_dto_from_domain(
    action_input: CreateDocumentInput,
) -> CreateDocumentInputDTO:
    return CreateDocumentInputDTO(
        title=action_input.title,
        body=action_input.body,
        folder_id=action_input.folder_id,
        metadata=dict(action_input.metadata),
    )


def update_document_input_dto_from_domain(
    action_input: UpdateDocumentInput,
) -> UpdateDocumentInputDTO:
    return UpdateDocumentInputDTO(
        document_type=action_input.document_type,
        document_id=action_input.document_id,
        title=action_input.title,
        body=action_input.body,
        metadata=dict(action_input.metadata),
    )


def move_document_input_dto_from_domain(
    action_input: MoveDocumentInput,
) -> MoveDocumentInputDTO:
    return MoveDocumentInputDTO(
        document_type=action_input.document_type,
        document_id=action_input.document_id,
        target_folder_id=action_input.target_folder_id,
        source_folder_id=action_input.source_folder_id,
    )


def link_documents_input_dto_from_domain(
    action_input: LinkDocumentsInput,
) -> LinkDocumentsInputDTO:
    return LinkDocumentsInputDTO(
        source_type=action_input.source_type,
        source_id=action_input.source_id,
        target_type=action_input.target_type,
        target_id=action_input.target_id,
        relationship=action_input.relationship,
        metadata=dict(action_input.metadata),
    )


def host_action_input_dto_from_domain(
    action_input: HostActionInput,
) -> HostActionInputDTO:
    if isinstance(action_input, CreateFolderInput):
        return create_folder_input_dto_from_domain(action_input)
    if isinstance(action_input, CreateDocumentInput):
        return create_document_input_dto_from_domain(action_input)
    if isinstance(action_input, UpdateDocumentInput):
        return update_document_input_dto_from_domain(action_input)
    if isinstance(action_input, MoveDocumentInput):
        return move_document_input_dto_from_domain(action_input)
    if isinstance(action_input, LinkDocumentsInput):
        return link_documents_input_dto_from_domain(action_input)
    raise TypeError(f"Unsupported host action input: {type(action_input).__name__}")


def create_folder_output_from_dto(
    dto: CreateFolderOutputDTO,
) -> CreateFolderOutput:
    return CreateFolderOutput(
        folder_id=require_uuid(dto.folder_id, "folder_id"),
        name=dto.name,
        parent_folder_id=require_optional_uuid(dto.parent_folder_id, "parent_folder_id"),
    )


def create_document_output_from_dto(
    dto: CreateDocumentOutputDTO,
) -> CreateDocumentOutput:
    return CreateDocumentOutput(
        created_document_id=require_uuid(
            dto.created_document_id,
            "created_document_id",
        ),
        created_document_type=require_non_blank(
            dto.created_document_type,
            "created_document_type",
        ),
        source_version=require_optional_non_blank(dto.source_version, "source_version"),
        folder_id=require_optional_uuid(dto.folder_id, "folder_id"),
    )


def update_document_output_from_dto(
    dto: UpdateDocumentOutputDTO,
) -> UpdateDocumentOutput:
    return UpdateDocumentOutput(
        updated_document_type=require_non_blank(
            dto.updated_document_type,
            "updated_document_type",
        ),
        updated_document_id=require_uuid(
            dto.updated_document_id,
            "updated_document_id",
        ),
        source_version=require_optional_non_blank(dto.source_version, "source_version"),
    )


def move_document_output_from_dto(
    dto: MoveDocumentOutputDTO,
) -> MoveDocumentOutput:
    return MoveDocumentOutput(
        moved_document_type=require_non_blank(
            dto.moved_document_type,
            "moved_document_type",
        ),
        moved_document_id=require_uuid(dto.moved_document_id, "moved_document_id"),
        target_folder_id=require_uuid(dto.target_folder_id, "target_folder_id"),
        source_folder_id=require_optional_uuid(
            dto.source_folder_id,
            "source_folder_id",
        ),
    )


def link_documents_output_from_dto(
    dto: LinkDocumentsOutputDTO,
) -> LinkDocumentsOutput:
    return LinkDocumentsOutput(
        source_type=require_non_blank(dto.source_type, "source_type"),
        source_id=require_uuid(dto.source_id, "source_id"),
        target_type=require_non_blank(dto.target_type, "target_type"),
        target_id=require_uuid(dto.target_id, "target_id"),
        relationship=require_non_blank(dto.relationship, "relationship"),
        link_id=require_optional_non_blank(dto.link_id, "link_id"),
    )


def host_action_output_from_dto(
    dto: HostActionOutputDTO | None,
) -> HostActionOutput | None:
    if dto is None:
        return None
    if isinstance(dto, CreateFolderOutputDTO):
        return create_folder_output_from_dto(dto)
    if isinstance(dto, CreateDocumentOutputDTO):
        return create_document_output_from_dto(dto)
    if isinstance(dto, UpdateDocumentOutputDTO):
        return update_document_output_from_dto(dto)
    if isinstance(dto, MoveDocumentOutputDTO):
        return move_document_output_from_dto(dto)
    if isinstance(dto, LinkDocumentsOutputDTO):
        return link_documents_output_from_dto(dto)
    raise TypeError(f"Unsupported host action output: {type(dto).__name__}")


def host_action_policy_dto_from_domain(
    policy: HostActionPolicy,
) -> HostActionPolicyDTO:
    return HostActionPolicyDTO(
        max_attempts=policy.max_attempts,
        allow_skip=policy.allow_skip,
        retryable=policy.retryable,
        requires_confirmation=policy.requires_confirmation,
    )


def host_action_dto_from_domain(action: HostAction) -> HostActionDTO:
    return HostActionDTO(
        action_type=cast(HostActionTypeDTO, action.action_type.value),
        summary=action.summary,
        action_id=action.action_id,
        reason=action.reason,
        status=cast(HostActionStatusDTO, action.status.value),
        input=host_action_input_dto_from_domain(action.input),
        attempts=action.attempts,
        policy=host_action_policy_dto_from_domain(action.policy),
        metadata=dict(action.metadata),
    )


def action_plan_dto_from_domain(plan: ActionPlan) -> ActionPlanDTO:
    return ActionPlanDTO(
        summary=plan.summary,
        steps=list(plan.steps),
        host_actions=[host_action_dto_from_domain(action) for action in plan.host_actions],
    )


def host_action_result_from_dto(
    dto: HostActionResultDTO,
) -> HostActionResult:
    return HostActionResult(
        action_id=require_uuid(dto.action_id, "action_id"),
        outcome=HostActionResultType(dto.outcome),
        action_type=HostActionType(dto.action_type) if dto.action_type else None,
        output=host_action_output_from_dto(dto.output),
        error=require_optional_non_blank(dto.error, "error"),
        metadata=dict(dto.metadata),
    )


def record_action_result_command_from_request(
    request: RecordHostActionResultRequest,
) -> RecordActionResultCommand:
    return RecordActionResultCommand(
        result=host_action_result_from_dto(request.result),
    )
