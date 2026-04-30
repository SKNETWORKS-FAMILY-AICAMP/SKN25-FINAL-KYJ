from __future__ import annotations

from ai_core.api.dto.action_inputs import (
    CreateDocumentInputDTO,
    HostActionInputDTO,
    LinkDocumentsInputDTO,
    MoveDocumentInputDTO,
    UpdateDocumentInputDTO,
)
from ai_core.api.dto.action_outputs import (
    CreateDocumentOutputDTO,
    HostActionResultOutputDTO,
    LinkDocumentsOutputDTO,
    MoveDocumentOutputDTO,
    UpdateDocumentOutputDTO,
)
from ai_core.api.dto.base import APIBaseDTO
from ai_core.application.models.actions import (
    CreateDocumentInput,
    CreateDocumentOutput,
    HostActionInput,
    HostActionOutput,
    HostActionType,
    LinkDocumentsInput,
    LinkDocumentsOutput,
    MoveDocumentInput,
    MoveDocumentOutput,
    UpdateDocumentInput,
    UpdateDocumentOutput,
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
