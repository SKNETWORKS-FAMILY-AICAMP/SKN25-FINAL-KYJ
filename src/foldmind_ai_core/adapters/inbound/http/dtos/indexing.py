from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO
from foldmind_ai_core.adapters.inbound.http.dtos.documents import (
    RetrievedFolderDTO,
    SourceDocumentDTO,
    SourceFolderDTO,
)


class IndexDocumentRequest(APIDTO):
    document: SourceDocumentDTO


class IndexDocumentResponse(APIDTO):
    indexed_chunk_count: int


class UpdateDocumentFolderRelationsRequest(APIDTO):
    tenant: str
    source_version: str
    folder_ids: tuple[str, ...] = ()


class IndexFolderRequest(APIDTO):
    folder: SourceFolderDTO


class IndexFolderResponse(APIDTO):
    folder: RetrievedFolderDTO
