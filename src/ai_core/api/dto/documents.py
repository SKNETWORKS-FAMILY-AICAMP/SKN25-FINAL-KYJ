from __future__ import annotations

from typing import Any

from pydantic import Field

from ai_core.api.dto.base import APIBaseDTO, to_plain
from ai_core.domain.documents import IndexedDocument, SourceDocument
from ai_core.domain.folders import IndexedFolder


class SourceDocumentDTO(APIBaseDTO):
    tenant: str
    entity_type: str
    entity_id: str
    version: str
    title: str
    body: str
    folder_ids: tuple[str, ...] = Field(default_factory=tuple)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, document: SourceDocument) -> SourceDocumentDTO:
        return cls(
            tenant=document.tenant,
            entity_type=document.entity_type,
            entity_id=document.entity_id,
            version=document.version,
            title=document.title,
            body=document.body,
            folder_ids=document.folder_ids,
            tags=document.tags,
            metadata=to_plain(document.metadata),
        )

    def to_model(self) -> SourceDocument:
        return SourceDocument(
            tenant=self.tenant,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            version=self.version,
            title=self.title,
            body=self.body,
            folder_ids=self.folder_ids,
            tags=self.tags,
            metadata=dict(self.metadata),
        )


class IndexedDocumentDTO(APIBaseDTO):
    tenant: str
    entity_type: str
    entity_id: str
    source_key: str
    snippet: str
    folder_ids: tuple[str, ...] = Field(default_factory=tuple)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, document: IndexedDocument) -> IndexedDocumentDTO:
        return cls(
            tenant=document.tenant,
            entity_type=document.entity_type,
            entity_id=document.entity_id,
            source_key=document.source_key,
            snippet=document.snippet,
            folder_ids=document.folder_ids,
            tags=document.tags,
            metadata=to_plain(document.metadata),
        )


class IndexedFolderDTO(APIBaseDTO):
    tenant: str
    folder_id: str
    name: str
    path: str | None = None
    parent_folder_id: str | None = None
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, folder: IndexedFolder) -> IndexedFolderDTO:
        return cls(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            name=folder.name,
            path=folder.path,
            parent_folder_id=folder.parent_folder_id,
            description=folder.description,
            metadata=to_plain(folder.metadata),
        )
