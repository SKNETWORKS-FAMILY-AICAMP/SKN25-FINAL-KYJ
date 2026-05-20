from __future__ import annotations

from fastapi import APIRouter, status

from foldmind_ai_core.adapters.inbound.http.application_errors import ApplicationErrorRoute
from foldmind_ai_core.adapters.inbound.http.dtos.indexing import (
    IndexDocumentRequest,
    IndexDocumentResponse,
    IndexFolderRequest,
    IndexFolderResponse,
    UpdateDocumentFolderRelationsRequest,
)
from foldmind_ai_core.adapters.inbound.http.mappers.indexing import (
    delete_document_index_command_from_document_id,
    delete_folder_index_command_from_folder_id,
    index_document_command_from_request,
    index_document_response_from_result,
    index_folder_command_from_request,
    index_folder_response_from_result,
    update_document_folder_relations_command_from_request,
)
from foldmind_ai_core.core.application.ports.inbound.indexing import (
    DeleteDocumentIndexInboundPort,
    DeleteFolderIndexInboundPort,
    IndexDocumentInboundPort,
    IndexFolderInboundPort,
    UpdateDocumentFolderRelationsInboundPort,
)


def create_indexing_router(
    *,
    index_document: IndexDocumentInboundPort,
    delete_document_index: DeleteDocumentIndexInboundPort,
    update_document_folder_relations: UpdateDocumentFolderRelationsInboundPort,
    index_folder: IndexFolderInboundPort,
    delete_folder_index: DeleteFolderIndexInboundPort,
) -> APIRouter:
    router = APIRouter(
        prefix="/indexing",
        tags=["indexing"],
        route_class=ApplicationErrorRoute,
    )

    @router.post("/documents", response_model=IndexDocumentResponse)
    def index_document_endpoint(request: IndexDocumentRequest) -> IndexDocumentResponse:
        result = index_document.execute(index_document_command_from_request(request))
        return index_document_response_from_result(result)

    @router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_document_index_endpoint(
        document_id: str,
    ) -> None:
        delete_document_index.execute(
            delete_document_index_command_from_document_id(document_id)
        )

    @router.put(
        "/documents/{document_id}/folder-relations",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def update_document_folder_relations_endpoint(
        document_id: str,
        request: UpdateDocumentFolderRelationsRequest,
    ) -> None:
        update_document_folder_relations.execute(
            update_document_folder_relations_command_from_request(
                document_id=document_id,
                request=request,
            )
        )

    @router.post("/folders", response_model=IndexFolderResponse)
    def index_folder_endpoint(request: IndexFolderRequest) -> IndexFolderResponse:
        result = index_folder.execute(index_folder_command_from_request(request))
        return index_folder_response_from_result(result)

    @router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_folder_index_endpoint(
        folder_id: str,
    ) -> None:
        delete_folder_index.execute(
            delete_folder_index_command_from_folder_id(folder_id)
        )

    return router
