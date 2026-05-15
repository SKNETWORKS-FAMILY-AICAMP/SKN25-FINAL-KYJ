from __future__ import annotations

from fastapi import APIRouter

from foldmind_ai_core.adapters.inbound.http.error_handlers import invalid_input_response
from foldmind_ai_core.adapters.inbound.http.schemas.documents import RetrievedFolderDTO
from foldmind_ai_core.adapters.inbound.http.schemas.indexing import (
    DeleteDocumentIndexRequest,
    DeleteDocumentIndexResponse,
    DeleteFolderIndexRequest,
    DeleteFolderIndexResponse,
    IndexDocumentRequest,
    IndexDocumentResponse,
    IndexFolderRequest,
    IndexFolderResponse,
)
from foldmind_ai_core.application.ports.inbound.indexing_use_case import (
    DeleteDocumentIndexUseCasePort,
    DeleteFolderIndexUseCasePort,
    IndexDocumentUseCasePort,
    IndexFolderUseCasePort,
)
from foldmind_ai_core.shared.validation import InvalidInputError


def create_indexing_router(
    *,
    index_document: IndexDocumentUseCasePort,
    delete_document_index: DeleteDocumentIndexUseCasePort,
    index_folder: IndexFolderUseCasePort,
    delete_folder_index: DeleteFolderIndexUseCasePort,
) -> APIRouter:
    router = APIRouter(prefix="/indexing", tags=["indexing"])

    @router.post("/documents", response_model=IndexDocumentResponse)
    def index_document_endpoint(request: IndexDocumentRequest) -> IndexDocumentResponse:
        try:
            chunks = index_document.execute(request.to_model())
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        return IndexDocumentResponse(indexed_chunk_count=len(chunks))

    @router.post("/documents/delete", response_model=DeleteDocumentIndexResponse)
    def delete_document_index_endpoint(
        request: DeleteDocumentIndexRequest,
    ) -> DeleteDocumentIndexResponse:
        try:
            request.validate_request()
            delete_document_index.execute(
                document_id=request.document_id,
            )
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        return DeleteDocumentIndexResponse(deleted=True)

    @router.post("/folders", response_model=IndexFolderResponse)
    def index_folder_endpoint(request: IndexFolderRequest) -> IndexFolderResponse:
        try:
            folder = index_folder.execute(request.to_model())
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        return IndexFolderResponse(folder=RetrievedFolderDTO.from_model(folder))

    @router.post("/folders/delete", response_model=DeleteFolderIndexResponse)
    def delete_folder_index_endpoint(
        request: DeleteFolderIndexRequest,
    ) -> DeleteFolderIndexResponse:
        try:
            request.validate_request()
            delete_folder_index.execute(
                folder_id=request.folder_id,
            )
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        return DeleteFolderIndexResponse(deleted=True)

    return router
