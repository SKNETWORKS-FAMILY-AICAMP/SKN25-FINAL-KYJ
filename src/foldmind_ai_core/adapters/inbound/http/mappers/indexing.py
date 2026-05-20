from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.dtos.indexing import (
    IndexDocumentRequest,
    IndexDocumentResponse,
    IndexFolderRequest,
    IndexFolderResponse,
    UpdateDocumentFolderRelationsRequest,
)
from foldmind_ai_core.adapters.inbound.http.dtos.documents import RetrievedFolderDTO
from foldmind_ai_core.adapters.inbound.http.mappers.documents import (
    index_document_command_from_dto,
    index_folder_command_from_dto,
)
from foldmind_ai_core.core.application.commands.indexing import (
    DeleteDocumentIndexCommand,
    DeleteFolderIndexCommand,
    IndexDocumentCommand,
    IndexFolderCommand,
    UpdateDocumentFolderRelationsCommand,
)
from foldmind_ai_core.core.application.results.indexing import (
    IndexDocumentResult,
    IndexFolderResult,
)
from foldmind_ai_core.shared.validation import (
    require_non_blank,
    require_uuid,
    require_uuid_items,
)


def index_document_command_from_request(
    request: IndexDocumentRequest,
) -> IndexDocumentCommand:
    return index_document_command_from_dto(request.document)


def update_document_folder_relations_command_from_request(
    *,
    document_id: str,
    request: UpdateDocumentFolderRelationsRequest,
) -> UpdateDocumentFolderRelationsCommand:
    return UpdateDocumentFolderRelationsCommand(
        tenant=require_non_blank(request.tenant, "tenant"),
        document_id=require_uuid(document_id, "document_id"),
        source_version=require_non_blank(request.source_version, "source_version"),
        folder_ids=_unique_uuid_items(request.folder_ids, "folder_ids"),
    )


def delete_document_index_command_from_document_id(
    document_id: str,
) -> DeleteDocumentIndexCommand:
    return DeleteDocumentIndexCommand(
        document_id=require_uuid(document_id, "document_id"),
    )


def _unique_uuid_items(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in require_uuid_items(values, field_name):
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return tuple(unique)


def index_folder_command_from_request(request: IndexFolderRequest) -> IndexFolderCommand:
    return index_folder_command_from_dto(request.folder)


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


def index_folder_response_from_result(result: IndexFolderResult) -> IndexFolderResponse:
    return IndexFolderResponse(
        folder=RetrievedFolderDTO(
            tenant=result.tenant,
            folder_id=result.folder_id,
            source_version=result.source_version,
        )
    )
