from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.schemas.base import APIBaseDTO
from foldmind_ai_core.adapters.inbound.http.schemas.documents import (
    RetrievedFolderDTO,
    SourceDocumentDTO,
    SourceFolderDTO,
)
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.reference.folders import SourceFolder
from foldmind_ai_core.shared.validation import require_uuid


class IndexDocumentRequest(APIBaseDTO):
    document: SourceDocumentDTO

    def to_model(self) -> SourceDocument:
        return self.document.to_model()


class IndexDocumentResponse(APIBaseDTO):
    indexed_chunk_count: int


class DeleteDocumentIndexRequest(APIBaseDTO):
    document_id: str

    def validate_request(self) -> None:
        require_uuid(self.document_id, "document_id")


class DeleteDocumentIndexResponse(APIBaseDTO):
    deleted: bool


class IndexFolderRequest(APIBaseDTO):
    folder: SourceFolderDTO

    def to_model(self) -> SourceFolder:
        return self.folder.to_model()


class IndexFolderResponse(APIBaseDTO):
    folder: RetrievedFolderDTO


class DeleteFolderIndexRequest(APIBaseDTO):
    folder_id: str

    def validate_request(self) -> None:
        require_uuid(self.folder_id, "folder_id")


class DeleteFolderIndexResponse(APIBaseDTO):
    deleted: bool
