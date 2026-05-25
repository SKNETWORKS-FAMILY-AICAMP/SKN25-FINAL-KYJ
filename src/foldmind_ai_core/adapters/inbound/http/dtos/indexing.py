from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.dtos.documents import (
    RetrievedFolderDTO,
    SourceDocumentDTO,
    SourceFolderDTO,
)
from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO


class IndexDocumentRequest(APIDTO):
    document: SourceDocumentDTO


class IndexDocumentResponse(APIDTO):
    indexed_chunk_count: int


class IndexFolderRequest(APIDTO):
    folder: SourceFolderDTO


class IndexFolderResponse(APIDTO):
    folder: RetrievedFolderDTO
