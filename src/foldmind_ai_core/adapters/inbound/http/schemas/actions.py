from __future__ import annotations

from typing import Any, TypeAlias

from pydantic import Field, model_validator

from foldmind_ai_core.adapters.inbound.http.schemas.base import APIBaseDTO
from foldmind_ai_core.domain.workflow.actions import (
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
    HostActionStatus,
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


class CreateFolderInputDTO(APIBaseDTO):
    name: str
    parent_folder_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, action_input: CreateFolderInput) -> CreateFolderInputDTO:
        return cls(
            name=action_input.name,
            parent_folder_id=action_input.parent_folder_id,
            metadata=dict(action_input.metadata),
        )


class CreateDocumentInputDTO(APIBaseDTO):
    title: str
    body: str
    folder_id: str | None = None
    tag_ids: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, action_input: CreateDocumentInput) -> CreateDocumentInputDTO:
        return cls(
            title=action_input.title,
            body=action_input.body,
            folder_id=action_input.folder_id,
            tag_ids=action_input.tag_ids,
            metadata=dict(action_input.metadata),
        )


class UpdateDocumentInputDTO(APIBaseDTO):
    document_type: str
    document_id: str
    title: str | None = None
    body: str | None = None
    tag_ids: tuple[str, ...] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, action_input: UpdateDocumentInput) -> UpdateDocumentInputDTO:
        return cls(
            document_type=action_input.document_type,
            document_id=action_input.document_id,
            title=action_input.title,
            body=action_input.body,
            tag_ids=action_input.tag_ids,
            metadata=dict(action_input.metadata),
        )


class MoveDocumentInputDTO(APIBaseDTO):
    document_type: str
    document_id: str
    target_folder_id: str
    source_folder_id: str | None = None

    @classmethod
    def from_model(cls, action_input: MoveDocumentInput) -> MoveDocumentInputDTO:
        return cls(
            document_type=action_input.document_type,
            document_id=action_input.document_id,
            target_folder_id=action_input.target_folder_id,
            source_folder_id=action_input.source_folder_id,
        )


class LinkDocumentsInputDTO(APIBaseDTO):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str = "related"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, action_input: LinkDocumentsInput) -> LinkDocumentsInputDTO:
        return cls(
            source_type=action_input.source_type,
            source_id=action_input.source_id,
            target_type=action_input.target_type,
            target_id=action_input.target_id,
            relationship=action_input.relationship,
            metadata=dict(action_input.metadata),
        )


HostActionInputDTO: TypeAlias = (
    CreateFolderInputDTO
    | CreateDocumentInputDTO
    | UpdateDocumentInputDTO
    | MoveDocumentInputDTO
    | LinkDocumentsInputDTO
)


class CreateFolderOutputDTO(APIBaseDTO):
    folder_id: str
    name: str | None = None
    parent_folder_id: str | None = None

    @classmethod
    def from_model(cls, output: CreateFolderOutput) -> CreateFolderOutputDTO:
        return cls(
            folder_id=output.folder_id,
            name=output.name,
            parent_folder_id=output.parent_folder_id,
        )

    def to_model(self) -> CreateFolderOutput:
        require_uuid(self.folder_id, "folder_id")
        require_optional_uuid(self.parent_folder_id, "parent_folder_id")
        return CreateFolderOutput(
            folder_id=self.folder_id,
            name=self.name,
            parent_folder_id=self.parent_folder_id,
        )


class CreateDocumentOutputDTO(APIBaseDTO):
    created_document_id: str
    created_document_type: str = "document"
    source_version: str | None = None
    folder_id: str | None = None

    @classmethod
    def from_model(cls, output: CreateDocumentOutput) -> CreateDocumentOutputDTO:
        return cls(
            created_document_id=output.created_document_id,
            created_document_type=output.created_document_type,
            source_version=output.source_version,
            folder_id=output.folder_id,
        )

    def to_model(self) -> CreateDocumentOutput:
        require_uuid(self.created_document_id, "created_document_id")
        require_non_blank(self.created_document_type, "created_document_type")
        require_optional_non_blank(self.source_version, "source_version")
        require_optional_uuid(self.folder_id, "folder_id")
        return CreateDocumentOutput(
            created_document_id=self.created_document_id,
            created_document_type=self.created_document_type,
            source_version=self.source_version,
            folder_id=self.folder_id,
        )


class UpdateDocumentOutputDTO(APIBaseDTO):
    updated_document_type: str
    updated_document_id: str
    source_version: str | None = None

    @classmethod
    def from_model(cls, output: UpdateDocumentOutput) -> UpdateDocumentOutputDTO:
        return cls(
            updated_document_type=output.updated_document_type,
            updated_document_id=output.updated_document_id,
            source_version=output.source_version,
        )

    def to_model(self) -> UpdateDocumentOutput:
        require_non_blank(self.updated_document_type, "updated_document_type")
        require_uuid(self.updated_document_id, "updated_document_id")
        require_optional_non_blank(self.source_version, "source_version")
        return UpdateDocumentOutput(
            updated_document_type=self.updated_document_type,
            updated_document_id=self.updated_document_id,
            source_version=self.source_version,
        )


class MoveDocumentOutputDTO(APIBaseDTO):
    moved_document_type: str
    moved_document_id: str
    target_folder_id: str
    source_folder_id: str | None = None

    @classmethod
    def from_model(cls, output: MoveDocumentOutput) -> MoveDocumentOutputDTO:
        return cls(
            moved_document_type=output.moved_document_type,
            moved_document_id=output.moved_document_id,
            target_folder_id=output.target_folder_id,
            source_folder_id=output.source_folder_id,
        )

    def to_model(self) -> MoveDocumentOutput:
        require_non_blank(self.moved_document_type, "moved_document_type")
        require_uuid(self.moved_document_id, "moved_document_id")
        require_uuid(self.target_folder_id, "target_folder_id")
        require_optional_uuid(self.source_folder_id, "source_folder_id")
        return MoveDocumentOutput(
            moved_document_type=self.moved_document_type,
            moved_document_id=self.moved_document_id,
            target_folder_id=self.target_folder_id,
            source_folder_id=self.source_folder_id,
        )


class LinkDocumentsOutputDTO(APIBaseDTO):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str = "related"
    link_id: str | None = None

    @classmethod
    def from_model(cls, output: LinkDocumentsOutput) -> LinkDocumentsOutputDTO:
        return cls(
            source_type=output.source_type,
            source_id=output.source_id,
            target_type=output.target_type,
            target_id=output.target_id,
            relationship=output.relationship,
            link_id=output.link_id,
        )

    def to_model(self) -> LinkDocumentsOutput:
        require_non_blank(self.source_type, "source_type")
        require_uuid(self.source_id, "source_id")
        require_non_blank(self.target_type, "target_type")
        require_uuid(self.target_id, "target_id")
        require_non_blank(self.relationship, "relationship")
        require_optional_non_blank(self.link_id, "link_id")
        return LinkDocumentsOutput(
            source_type=self.source_type,
            source_id=self.source_id,
            target_type=self.target_type,
            target_id=self.target_id,
            relationship=self.relationship,
            link_id=self.link_id,
        )


HostActionResultOutputDTO: TypeAlias = (
    CreateFolderOutputDTO
    | CreateDocumentOutputDTO
    | UpdateDocumentOutputDTO
    | MoveDocumentOutputDTO
    | LinkDocumentsOutputDTO
)

INPUT_DTO_BY_ACTION_TYPE: dict[HostActionType, type[APIBaseDTO]] = {
    HostActionType.CREATE_FOLDER: CreateFolderInputDTO,
    HostActionType.CREATE_DOCUMENT: CreateDocumentInputDTO,
    HostActionType.UPDATE_DOCUMENT: UpdateDocumentInputDTO,
    HostActionType.MOVE_DOCUMENT: MoveDocumentInputDTO,
    HostActionType.LINK_DOCUMENTS: LinkDocumentsInputDTO,
}

OUTPUT_DTO_BY_ACTION_TYPE: dict[HostActionType, type[APIBaseDTO]] = {
    HostActionType.CREATE_FOLDER: CreateFolderOutputDTO,
    HostActionType.CREATE_DOCUMENT: CreateDocumentOutputDTO,
    HostActionType.UPDATE_DOCUMENT: UpdateDocumentOutputDTO,
    HostActionType.MOVE_DOCUMENT: MoveDocumentOutputDTO,
    HostActionType.LINK_DOCUMENTS: LinkDocumentsOutputDTO,
}

_INPUT_DTO_BY_MODEL_TYPE: tuple[tuple[type[HostActionInput], type[APIBaseDTO]], ...] = (
    (CreateFolderInput, CreateFolderInputDTO),
    (CreateDocumentInput, CreateDocumentInputDTO),
    (UpdateDocumentInput, UpdateDocumentInputDTO),
    (MoveDocumentInput, MoveDocumentInputDTO),
    (LinkDocumentsInput, LinkDocumentsInputDTO),
)

_OUTPUT_DTO_BY_MODEL_TYPE: tuple[tuple[type[HostActionOutput], type[APIBaseDTO]], ...] = (
    (CreateFolderOutput, CreateFolderOutputDTO),
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
        require_uuid(self.action_id, "action_id")
        require_optional_non_blank(self.error, "error")
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
    result: HostActionResultDTO

    def to_model_result(self) -> HostActionResult:
        return self.result.to_model()
