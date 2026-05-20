from __future__ import annotations

from typing import Any, Literal, TypeAlias

from pydantic import Field, model_validator

from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO

HostActionTypeDTO: TypeAlias = Literal[
    "create_folder",
    "create_document",
    "update_document",
    "move_document",
    "link_documents",
]
HostActionStatusDTO: TypeAlias = Literal[
    "proposed",
    "ready",
    "succeeded",
    "failed",
    "skipped",
]
HostActionResultTypeDTO: TypeAlias = Literal[
    "approved",
    "rejected",
    "modified",
    "succeeded",
    "failed",
    "retry",
    "skipped",
]


class CreateFolderInputDTO(APIDTO):
    name: str
    parent_folder_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateDocumentInputDTO(APIDTO):
    title: str
    body: str
    folder_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateDocumentInputDTO(APIDTO):
    document_type: str
    document_id: str
    title: str | None = None
    body: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MoveDocumentInputDTO(APIDTO):
    document_type: str
    document_id: str
    target_folder_id: str
    source_folder_id: str | None = None


class LinkDocumentsInputDTO(APIDTO):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str = "related"
    metadata: dict[str, Any] = Field(default_factory=dict)


HostActionInputDTO: TypeAlias = (
    CreateFolderInputDTO
    | CreateDocumentInputDTO
    | UpdateDocumentInputDTO
    | MoveDocumentInputDTO
    | LinkDocumentsInputDTO
)


class CreateFolderOutputDTO(APIDTO):
    folder_id: str
    name: str | None = None
    parent_folder_id: str | None = None


class CreateDocumentOutputDTO(APIDTO):
    created_document_id: str
    created_document_type: str = "document"
    source_version: str | None = None
    folder_id: str | None = None


class UpdateDocumentOutputDTO(APIDTO):
    updated_document_type: str
    updated_document_id: str
    source_version: str | None = None


class MoveDocumentOutputDTO(APIDTO):
    moved_document_type: str
    moved_document_id: str
    target_folder_id: str
    source_folder_id: str | None = None


class LinkDocumentsOutputDTO(APIDTO):
    source_type: str
    source_id: str
    target_type: str
    target_id: str
    relationship: str = "related"
    link_id: str | None = None


HostActionResultOutputDTO: TypeAlias = (
    CreateFolderOutputDTO
    | CreateDocumentOutputDTO
    | UpdateDocumentOutputDTO
    | MoveDocumentOutputDTO
    | LinkDocumentsOutputDTO
)

INPUT_DTO_BY_ACTION_TYPE: dict[str, type[APIDTO]] = {
    "create_folder": CreateFolderInputDTO,
    "create_document": CreateDocumentInputDTO,
    "update_document": UpdateDocumentInputDTO,
    "move_document": MoveDocumentInputDTO,
    "link_documents": LinkDocumentsInputDTO,
}

OUTPUT_DTO_BY_ACTION_TYPE: dict[str, type[APIDTO]] = {
    "create_folder": CreateFolderOutputDTO,
    "create_document": CreateDocumentOutputDTO,
    "update_document": UpdateDocumentOutputDTO,
    "move_document": MoveDocumentOutputDTO,
    "link_documents": LinkDocumentsOutputDTO,
}


class HostActionPolicyDTO(APIDTO):
    max_attempts: int = 1
    allow_skip: bool = False
    retryable: bool = False
    requires_confirmation: bool = True


class HostActionDTO(APIDTO):
    action_type: HostActionTypeDTO
    summary: str
    action_id: str | None = None
    reason: str = ""
    status: HostActionStatusDTO = "proposed"
    input: HostActionInputDTO
    attempts: int = 0
    policy: HostActionPolicyDTO = Field(default_factory=HostActionPolicyDTO)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_input_matches_action_type(self) -> HostActionDTO:
        expected_input_type = INPUT_DTO_BY_ACTION_TYPE[self.action_type]
        if not isinstance(self.input, expected_input_type):
            raise ValueError(
                f"{self.action_type} action requires {expected_input_type.__name__}."
            )
        return self


class ActionPlanDTO(APIDTO):
    summary: str
    steps: list[str] = Field(default_factory=list)
    host_actions: list[HostActionDTO] = Field(default_factory=list)


class HostActionResultDTO(APIDTO):
    action_id: str
    action_type: HostActionTypeDTO | None = None
    outcome: HostActionResultTypeDTO
    output: HostActionResultOutputDTO | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_output_matches_action_type(self) -> HostActionResultDTO:
        if self.output is None:
            if self.outcome == "succeeded" and self.error is not None and self.error.strip():
                raise ValueError("succeeded action results must not include error.")
            return self
        if self.outcome != "succeeded":
            raise ValueError("Only succeeded action results may include output.")
        if self.action_type is None:
            raise ValueError("action_type is required when action result output is present.")

        expected_output_type = OUTPUT_DTO_BY_ACTION_TYPE[self.action_type]
        if not isinstance(self.output, expected_output_type):
            raise ValueError(
                f"{self.action_type} result requires {expected_output_type.__name__}."
            )
        return self


class RecordHostActionResultRequest(APIDTO):
    result: HostActionResultDTO
