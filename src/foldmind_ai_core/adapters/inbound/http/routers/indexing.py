from __future__ import annotations

from fastapi import APIRouter, status

from foldmind_ai_core.adapters.inbound.http.application_errors import ApplicationErrorRoute
from foldmind_ai_core.adapters.inbound.http.dtos.indexing import (
    IndexDocumentRequest,
    IndexDocumentResponse,
    IndexFolderRequest,
    IndexFolderResponse,
)
from foldmind_ai_core.adapters.inbound.http.mappers.indexing import (
    delete_document_index_command_from_document_id,
    delete_folder_index_command_from_folder_id,
    index_document_command_from_request,
    index_document_response_from_result,
    index_folder_response_from_result,
    source_folder_from_request,
)
from foldmind_ai_core.core.application.ports.inbound.indexing import (
    DocumentIndexingServicePort,
    FolderIndexingServicePort,
)


def create_indexing_router(
    *,
    document_indexing: DocumentIndexingServicePort,
    folder_indexing: FolderIndexingServicePort,
) -> APIRouter:
    router = APIRouter(
        prefix="/indexing",
        tags=["indexing"],
        route_class=ApplicationErrorRoute,
    )

    @router.post("/documents", response_model=IndexDocumentResponse)
    async def index_document_endpoint(
        request: IndexDocumentRequest,
    ) -> IndexDocumentResponse:
        result = await document_indexing.index_document(
            index_document_command_from_request(request)
        )
        return index_document_response_from_result(result)

    @router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_document_index_endpoint(
        document_id: str,
    ) -> None:
        await document_indexing.delete_document(
            delete_document_index_command_from_document_id(document_id)
        )

    @router.post("/folders", response_model=IndexFolderResponse)
    async def index_folder_endpoint(request: IndexFolderRequest) -> IndexFolderResponse:
        result = await folder_indexing.index_folder(source_folder_from_request(request))
        return index_folder_response_from_result(result)

    @router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_folder_index_endpoint(
        folder_id: str,
    ) -> None:
        await folder_indexing.delete_folder(
            delete_folder_index_command_from_folder_id(folder_id)
        )

    return router
