from __future__ import annotations

from typing import TypeAlias

from ai_core.api.dto.base import APIBaseDTO
from ai_core.application.models.actions import (
    CreateDocumentOutput,
    LinkDocumentsOutput,
    MoveDocumentOutput,
    UpdateDocumentOutput,
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
