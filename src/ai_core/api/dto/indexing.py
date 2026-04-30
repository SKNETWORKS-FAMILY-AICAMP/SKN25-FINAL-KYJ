from __future__ import annotations

from ai_core.api.dto.base import APIBaseDTO
from ai_core.api.dto.documents import SourceDocumentDTO
from ai_core.domain.documents import SourceDocument


class IndexDocumentRequest(APIBaseDTO):
    document: SourceDocumentDTO

    def to_model(self) -> SourceDocument:
        return self.document.to_model()


class IndexDocumentResponse(APIBaseDTO):
    indexed_chunk_count: int


class DeleteDocumentIndexRequest(APIBaseDTO):
    tenant: str
    entity_type: str
    entity_id: str


class DeleteDocumentIndexResponse(APIBaseDTO):
    deleted: bool
