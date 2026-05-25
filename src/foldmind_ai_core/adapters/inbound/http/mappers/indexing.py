from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.dtos.documents import RetrievedFolderDTO
from foldmind_ai_core.adapters.inbound.http.dtos.indexing import (
    IndexDocumentRequest,
    IndexDocumentResponse,
    IndexFolderRequest,
    IndexFolderResponse,
)
from foldmind_ai_core.adapters.inbound.http.mappers.documents import (
    index_document_command_from_dto,
    source_folder_from_dto,
)
from foldmind_ai_core.core.application.models.indexing import (
    DeleteDocumentIndexCommand,
    DeleteFolderIndexCommand,
    IndexDocumentCommand,
)
from foldmind_ai_core.core.application.models.indexing import IndexDocumentResult
from foldmind_ai_core.core.domain.models.folder_sources import (
    FolderSourceIdentity,
    SourceFolder,
)
from foldmind_ai_core.shared.validation import (
    require_uuid,
)


def index_document_command_from_request(
    request: IndexDocumentRequest,
) -> IndexDocumentCommand:
    return index_document_command_from_dto(request.document)


def delete_document_index_command_from_document_id(
    document_id: str,
) -> DeleteDocumentIndexCommand:
    return DeleteDocumentIndexCommand(
        document_id=require_uuid(document_id, "document_id"),
    )


def source_folder_from_request(request: IndexFolderRequest) -> SourceFolder:
    return source_folder_from_dto(request.folder)


def delete_folder_index_command_from_folder_id(
    folder_id: str,
) -> DeleteFolderIndexCommand:
    return DeleteFolderIndexCommand(
        folder_id=require_uuid(folder_id, "folder_id"),
    )


def index_document_response_from_result(
    result: IndexDocumentResult,
) -> IndexDocumentResponse:
    return IndexDocumentResponse(indexed_chunk_count=result.indexed_chunk_count)


def index_folder_response_from_result(
    result: FolderSourceIdentity,
) -> IndexFolderResponse:
    return IndexFolderResponse(
        folder=RetrievedFolderDTO(
            tenant=result.tenant,
            folder_id=result.folder_id,
            source_version=result.source_version,
        )
    )
