from __future__ import annotations

from fastapi import APIRouter, HTTPException

from foldmind_ai_core.adapters.inbound.http.error_handlers import invalid_input_response
from foldmind_ai_core.adapters.inbound.http.schemas.retrieval import (
    AnswerQuestionRequest,
    GeneratedTextResponse,
    RecommendFolderRequest,
    RecommendFolderResponse,
    SearchDocumentsRequest,
    SearchDocumentsResponse,
)
from foldmind_ai_core.application.errors import NoCandidatesError
from foldmind_ai_core.application.ports.inbound.recommendation_use_case import (
    RecommendFolderUseCasePort,
)
from foldmind_ai_core.application.ports.inbound.retrieval_use_case import (
    AnswerQuestionUseCasePort,
    SearchDocumentsUseCasePort,
)
from foldmind_ai_core.shared.validation import InvalidInputError


def create_retrieval_router(
    *,
    search_documents: SearchDocumentsUseCasePort,
    answer_question: AnswerQuestionUseCasePort,
    recommend_folder: RecommendFolderUseCasePort,
) -> APIRouter:
    router = APIRouter(prefix="/retrieval", tags=["retrieval"])

    @router.post("/search", response_model=SearchDocumentsResponse)
    def search_documents_endpoint(request: SearchDocumentsRequest) -> SearchDocumentsResponse:
        try:
            results = search_documents.execute(request.to_model())
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        return SearchDocumentsResponse.from_model(results)

    @router.post("/answer", response_model=GeneratedTextResponse)
    def answer_question_endpoint(request: AnswerQuestionRequest) -> GeneratedTextResponse:
        try:
            result = answer_question.execute(request.to_model())
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        return GeneratedTextResponse.from_model(result)

    @router.post("/folder-recommendations", response_model=RecommendFolderResponse)
    def recommend_folder_endpoint(request: RecommendFolderRequest) -> RecommendFolderResponse:
        try:
            result = recommend_folder.execute(request.to_model())
        except InvalidInputError as exc:
            raise invalid_input_response(exc) from exc
        except NoCandidatesError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return RecommendFolderResponse.from_model(result)

    return router
