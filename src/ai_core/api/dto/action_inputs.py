from __future__ import annotations

from typing import Any, TypeAlias

from pydantic import Field

from ai_core.api.dto.base import APIBaseDTO
from ai_core.application.models.actions import (
    CreateDocumentInput,
    LinkDocumentsInput,
    MoveDocumentInput,
    UpdateDocumentInput,
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
