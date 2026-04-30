from __future__ import annotations

from typing import Any, TypeAlias

from pydantic import Field, model_validator

from ai_core.api.dto.base import APIBaseDTO
from ai_core.application.models.actions import (
    ActionPlan,
    CreateDocumentInput,
    CreateDocumentOutput,
    HostAction,
    HostActionInput,
    HostActionOutput,
    HostActionPolicy,
    HostActionResult,
    HostActionResultType,
    HostActionStatus,
    HostActionType,
    LinkDocumentsInput,
    LinkDocumentsOutput,
    MoveDocumentInput,
    MoveDocumentOutput,
    UpdateDocumentInput,
    UpdateDocumentOutput,
)


class CreateDocumentInputDTO(APIBaseDTO):
    title: str
    body: str
    folder_id: str | None = None
    tags: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, action_input: CreateDocumentInput) -> CreateDocumentInputDTO:
        return cls(
            title=action_input.title,
            body=action_input.body,
            folder_id=action_input.folder_id,
            tags=action_input.tags,
            metadata=dict(action_input.metadata),
        )


class UpdateDocumentInputDTO(APIBaseDTO):
    entity_type: str
    entity_id: str
    title: str | None = None
    body: str | None = None
    tags: tuple[str, ...] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, action_input: UpdateDocumentInput) -> UpdateDocumentInputDTO:
        return cls(
            entity_type=action_input.entity_type,
            entity_id=action_input.entity_id,
            title=action_input.title,
            body=action_input.body,
            tags=action_input.tags,
            metadata=dict(action_input.metadata),
        )


class MoveDocumentInputDTO(APIBaseDTO):
    entity_type: str
    entity_id: str
    target_folder_id: str
    source_folder_id: str | None = None

    @classmethod
    def from_model(cls, action_input: MoveDocumentInput) -> MoveDocumentInputDTO:
        return cls(
            entity_type=action_input.entity_type,
            entity_id=action_input.entity_id,
            target_folder_id=action_input.target_folder_id,
            source_folder_id=action_input.source_folder_id,
        )


class LinkDocumentsInputDTO(APIBaseDTO):
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    relationship: str = "related"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, action_input: LinkDocumentsInput) -> LinkDocumentsInputDTO:
        return cls(
            source_entity_type=action_input.source_entity_type,
            source_entity_id=action_input.source_entity_id,
            target_entity_type=action_input.target_entity_type,
            target_entity_id=action_input.target_entity_id,
            relationship=action_input.relationship,
            metadata=dict(action_input.metadata),
        )


HostActionInputDTO: TypeAlias = (
    CreateDocumentInputDTO
    | UpdateDocumentInputDTO
    | MoveDocumentInputDTO
    | LinkDocumentsInputDTO
)


class CreateDocumentOutputDTO(APIBaseDTO):
    created_entity_id: str
    created_entity_type: str = "document"
    version: str | None = None
    folder_id: str | None = None

    @classmethod
    def from_model(cls, output: CreateDocumentOutput) -> CreateDocumentOutputDTO:
        return cls(
            created_entity_id=output.created_entity_id,
            created_entity_type=output.created_entity_type,
            version=output.version,
            folder_id=output.folder_id,
        )

    def to_model(self) -> CreateDocumentOutput:
        return CreateDocumentOutput(
            created_entity_id=self.created_entity_id,
            created_entity_type=self.created_entity_type,
            version=self.version,
            folder_id=self.folder_id,
        )


class UpdateDocumentOutputDTO(APIBaseDTO):
    updated_entity_type: str
    updated_entity_id: str
    version: str | None = None

    @classmethod
    def from_model(cls, output: UpdateDocumentOutput) -> UpdateDocumentOutputDTO:
        return cls(
            updated_entity_type=output.updated_entity_type,
            updated_entity_id=output.updated_entity_id,
            version=output.version,
        )

    def to_model(self) -> UpdateDocumentOutput:
        return UpdateDocumentOutput(
            updated_entity_type=self.updated_entity_type,
            updated_entity_id=self.updated_entity_id,
            version=self.version,
        )


class MoveDocumentOutputDTO(APIBaseDTO):
    moved_entity_type: str
    moved_entity_id: str
    target_folder_id: str
    source_folder_id: str | None = None

    @classmethod
    def from_model(cls, output: MoveDocumentOutput) -> MoveDocumentOutputDTO:
        return cls(
            moved_entity_type=output.moved_entity_type,
            moved_entity_id=output.moved_entity_id,
            target_folder_id=output.target_folder_id,
            source_folder_id=output.source_folder_id,
        )

    def to_model(self) -> MoveDocumentOutput:
        return MoveDocumentOutput(
            moved_entity_type=self.moved_entity_type,
            moved_entity_id=self.moved_entity_id,
            target_folder_id=self.target_folder_id,
            source_folder_id=self.source_folder_id,
        )


class LinkDocumentsOutputDTO(APIBaseDTO):
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_entity_id: str
    relationship: str = "related"
    link_id: str | None = None

    @classmethod
    def from_model(cls, output: LinkDocumentsOutput) -> LinkDocumentsOutputDTO:
        return cls(
            source_entity_type=output.source_entity_type,
            source_entity_id=output.source_entity_id,
            target_entity_type=output.target_entity_type,
            target_entity_id=output.target_entity_id,
            relationship=output.relationship,
            link_id=output.link_id,
        )

    def to_model(self) -> LinkDocumentsOutput:
        return LinkDocumentsOutput(
            source_entity_type=self.source_entity_type,
            source_entity_id=self.source_entity_id,
            target_entity_type=self.target_entity_type,
            target_entity_id=self.target_entity_id,
            relationship=self.relationship,
            link_id=self.link_id,
        )


HostActionResultOutputDTO: TypeAlias = (
    CreateDocumentOutputDTO
    | UpdateDocumentOutputDTO
    | MoveDocumentOutputDTO
    | LinkDocumentsOutputDTO
)

INPUT_DTO_BY_ACTION_TYPE: dict[HostActionType, type[APIBaseDTO]] = {
    HostActionType.CREATE_DOCUMENT: CreateDocumentInputDTO,
    HostActionType.UPDATE_DOCUMENT: UpdateDocumentInputDTO,
    HostActionType.MOVE_DOCUMENT: MoveDocumentInputDTO,
    HostActionType.LINK_DOCUMENTS: LinkDocumentsInputDTO,
}

OUTPUT_DTO_BY_ACTION_TYPE: dict[HostActionType, type[APIBaseDTO]] = {
    HostActionType.CREATE_DOCUMENT: CreateDocumentOutputDTO,
    HostActionType.UPDATE_DOCUMENT: UpdateDocumentOutputDTO,
    HostActionType.MOVE_DOCUMENT: MoveDocumentOutputDTO,
    HostActionType.LINK_DOCUMENTS: LinkDocumentsOutputDTO,
}

_INPUT_DTO_BY_MODEL_TYPE: tuple[tuple[type[HostActionInput], type[APIBaseDTO]], ...] = (
    (CreateDocumentInput, CreateDocumentInputDTO),
    (UpdateDocumentInput, UpdateDocumentInputDTO),
    (MoveDocumentInput, MoveDocumentInputDTO),
    (LinkDocumentsInput, LinkDocumentsInputDTO),
)

_OUTPUT_DTO_BY_MODEL_TYPE: tuple[tuple[type[HostActionOutput], type[APIBaseDTO]], ...] = (
    (CreateDocumentOutput, CreateDocumentOutputDTO),
    (UpdateDocumentOutput, UpdateDocumentOutputDTO),
    (MoveDocumentOutput, MoveDocumentOutputDTO),
    (LinkDocumentsOutput, LinkDocumentsOutputDTO),
)


def host_action_type(value: HostActionType | str) -> HostActionType:
    return value if isinstance(value, HostActionType) else HostActionType(value)


def expected_input_dto_type(action_type: HostActionType | str) -> type[APIBaseDTO]:
    return INPUT_DTO_BY_ACTION_TYPE[host_action_type(action_type)]


def expected_output_dto_type(action_type: HostActionType | str) -> type[APIBaseDTO]:
    return OUTPUT_DTO_BY_ACTION_TYPE[host_action_type(action_type)]


def host_action_input_from_model(action_input: HostActionInput) -> HostActionInputDTO:
    for model_type, dto_type in _INPUT_DTO_BY_MODEL_TYPE:
        if isinstance(action_input, model_type):
            return dto_type.from_model(action_input)
    raise TypeError(f"Unsupported host action input: {type(action_input).__name__}")


def host_action_output_from_model(
    output: HostActionOutput | None,
) -> HostActionResultOutputDTO | None:
    if output is None:
        return None
    for model_type, dto_type in _OUTPUT_DTO_BY_MODEL_TYPE:
        if isinstance(output, model_type):
            return dto_type.from_model(output)
    raise TypeError(f"Unsupported host action output: {type(output).__name__}")


class HostActionPolicyDTO(APIBaseDTO):
    max_attempts: int = 1
    allow_skip: bool = False
    retryable: bool = False
    requires_confirmation: bool = True

    @classmethod
    def from_model(cls, policy: HostActionPolicy) -> HostActionPolicyDTO:
        return cls(
            max_attempts=policy.max_attempts,
            allow_skip=policy.allow_skip,
            retryable=policy.retryable,
            requires_confirmation=policy.requires_confirmation,
        )


class HostActionDTO(APIBaseDTO):
    action_type: HostActionType
    summary: str
    action_id: str | None = None
    reason: str = ""
    status: HostActionStatus = HostActionStatus.PROPOSED
    input: HostActionInputDTO
    attempts: int = 0
    depends_on: list[str] = Field(default_factory=list)
    policy: HostActionPolicyDTO = Field(default_factory=HostActionPolicyDTO)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_input_matches_action_type(self) -> HostActionDTO:
        expected_input_type = expected_input_dto_type(self.action_type)
        if not isinstance(self.input, expected_input_type):
            raise ValueError(
                f"{self.action_type} action requires {expected_input_type.__name__}."
            )
        return self

    @classmethod
    def from_model(cls, action: HostAction) -> HostActionDTO:
        return cls(
            action_type=host_action_type(action.action_type),
            summary=action.summary,
            action_id=action.action_id,
            reason=action.reason,
            status=action.status,
            input=host_action_input_from_model(action.input),
            attempts=action.attempts,
            depends_on=list(action.depends_on),
            policy=HostActionPolicyDTO.from_model(action.policy),
            metadata=dict(action.metadata),
        )


class ActionPlanDTO(APIBaseDTO):
    summary: str
    steps: list[str] = Field(default_factory=list)
    host_actions: list[HostActionDTO] = Field(default_factory=list)

    @classmethod
    def from_model(cls, plan: ActionPlan) -> ActionPlanDTO:
        return cls(
            summary=plan.summary,
            steps=list(plan.steps),
            host_actions=[HostActionDTO.from_model(action) for action in plan.host_actions],
        )


class HostActionResultDTO(APIBaseDTO):
    action_id: str
    action_type: HostActionType | None = None
    outcome: HostActionResultType
    output: HostActionResultOutputDTO | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_output_matches_action_type(self) -> HostActionResultDTO:
        if self.output is None:
            return self
        if self.action_type is None:
            raise ValueError("action_type is required when action result output is present.")

        expected_output_type = expected_output_dto_type(self.action_type)
        if not isinstance(self.output, expected_output_type):
            raise ValueError(
                f"{self.action_type} result requires {expected_output_type.__name__}."
            )
        return self

    @classmethod
    def from_model(cls, result: HostActionResult) -> HostActionResultDTO:
        action_type = (
            host_action_type(result.action_type)
            if result.action_type is not None
            else None
        )
        return cls(
            action_id=result.action_id,
            action_type=action_type,
            outcome=result.outcome,
            output=host_action_output_from_model(result.output),
            error=result.error,
            metadata=dict(result.metadata),
        )

    def to_model(self) -> HostActionResult:
        output = self.output.to_model() if self.output is not None else None
        return HostActionResult(
            action_id=self.action_id,
            outcome=self.outcome,
            action_type=str(self.action_type) if self.action_type is not None else None,
            output=output,
            error=self.error,
            metadata=dict(self.metadata),
        )


class RecordHostActionResultRequest(APIBaseDTO):
    tenant: str
    task_id: str
    result: HostActionResultDTO

    def to_model_result(self) -> HostActionResult:
        return self.result.to_model()


class RecordHostActionResultResponse(APIBaseDTO):
    recorded: bool
