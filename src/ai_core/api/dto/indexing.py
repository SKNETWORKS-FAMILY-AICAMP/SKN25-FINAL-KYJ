from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ai_core.domain.documents import SourceDocument


class SourceDocumentDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
            metadata=dict(document.metadata),
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


class IndexDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document: SourceDocumentDTO

    def to_model(self) -> SourceDocument:
        return self.document.to_model()


class IndexDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    indexed_chunk_count: int


class DeleteDocumentIndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant: str
    entity_type: str
    entity_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
