from __future__ import annotations

from typing import Any

from pydantic import Field

from foldmind_ai_core.adapters.inbound.http.schemas.base import APIBaseDTO, to_plain
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.reference.folders import SourceFolder
from foldmind_ai_core.domain.retrieval.results import RetrievedDocument, RetrievedFolder
from foldmind_ai_core.shared.validation import (
    require_non_blank,
    require_optional_uuid,
    require_uuid,
    require_uuid_items,
)


class SourceDocumentDTO(APIBaseDTO):
    tenant: str
    document_type: str
    document_id: str
    source_version: str
    title: str
    body: str
    folder_ids: tuple[str, ...] = Field(default_factory=tuple)
    tag_ids: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, document: SourceDocument) -> SourceDocumentDTO:
        return cls(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            title=document.title,
            body=document.body,
            folder_ids=document.folder_ids,
            tag_ids=document.tag_ids,
            metadata=to_plain(document.metadata),
        )

    def to_model(self) -> SourceDocument:
        require_non_blank(self.tenant, "tenant")
        require_non_blank(self.document_type, "document_type")
        require_uuid(self.document_id, "document_id")
        require_non_blank(self.source_version, "source_version")
        require_uuid_items(self.folder_ids, "folder_ids")
        require_uuid_items(self.tag_ids, "tag_ids")
        return SourceDocument(
            tenant=self.tenant,
            document_type=self.document_type,
            document_id=self.document_id,
            source_version=self.source_version,
            title=self.title,
            body=self.body,
            folder_ids=self.folder_ids,
            tag_ids=self.tag_ids,
            metadata=dict(self.metadata),
        )


class RetrievedDocumentDTO(APIBaseDTO):
    tenant: str
    document_type: str
    document_id: str
    source_version: str
    snippet: str
    profile_version: str | None = None
    profile_schema_version: str = ""
    concept_ids: tuple[str, ...] = Field(default_factory=tuple)
    profile_confidence: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, document: RetrievedDocument) -> RetrievedDocumentDTO:
        return cls(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            snippet=document.snippet,
            profile_version=document.profile_version,
            profile_schema_version=document.profile_schema_version,
            concept_ids=document.concept_ids,
            profile_confidence=document.profile_confidence,
            metadata=to_plain(document.metadata),
        )


class SourceFolderDTO(APIBaseDTO):
    tenant: str
    folder_id: str
    source_version: str
    name: str
    path: str | None = None
    parent_folder_id: str | None = None
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, folder: SourceFolder) -> SourceFolderDTO:
        return cls(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
            name=folder.name,
            path=folder.path,
            parent_folder_id=folder.parent_folder_id,
            description=folder.description,
            metadata=to_plain(folder.metadata),
        )

    def to_model(self) -> SourceFolder:
        require_non_blank(self.tenant, "tenant")
        require_uuid(self.folder_id, "folder_id")
        require_non_blank(self.source_version, "source_version")
        require_optional_uuid(self.parent_folder_id, "parent_folder_id")
        return SourceFolder(
            tenant=self.tenant,
            folder_id=self.folder_id,
            source_version=self.source_version,
            name=self.name,
            path=self.path,
            parent_folder_id=self.parent_folder_id,
            description=self.description,
            metadata=dict(self.metadata),
        )


class RetrievedFolderDTO(APIBaseDTO):
    tenant: str
    folder_id: str
    source_version: str

    @classmethod
    def from_model(cls, folder: RetrievedFolder) -> RetrievedFolderDTO:
        return cls(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
        )
