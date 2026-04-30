from __future__ import annotations

from fastapi import APIRouter

from ai_core.api.errors import invalid_input_response
from ai_core.api.dto.indexing import (
    DeleteDocumentIndexRequest,
    DeleteDocumentIndexResponse,
    IndexDocumentRequest,
    IndexDocumentResponse,
)
from ai_core.application.use_cases.delete_document_index import DeleteDocumentIndexUseCase
from ai_core.application.use_cases.index_document import IndexDocumentUseCase
from ai_core.common.validation import InvalidInputError


def create_indexing_router(
    *,
    index_document: IndexDocumentUseCase,
    delete_document_index: DeleteDocumentIndexUseCase,
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
            delete_document_index.execute(
                tenant=request.tenant,
                entity_type=request.entity_type,
                entity_id=request.entity_id,
            )
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        return DeleteDocumentIndexResponse(deleted=True)

    return router
