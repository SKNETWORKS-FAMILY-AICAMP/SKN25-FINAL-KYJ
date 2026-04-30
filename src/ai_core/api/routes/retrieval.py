from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ai_core.api.errors import invalid_input_response
from ai_core.api.dto.retrieval import (
    AnswerQuestionRequest,
    GeneratedTextResponse,
    RecommendFolderRequest,
    RecommendFolderResponse,
    SearchDocumentsRequest,
    SearchDocumentsResponse,
)
from ai_core.application.use_cases.answer_question import AnswerQuestionUseCase
from ai_core.application.use_cases.hybrid_search import HybridSearchUseCase
from ai_core.application.use_cases.recommend_folder import RecommendFolderUseCase
from ai_core.common.validation import InvalidInputError


def create_retrieval_router(
    *,
    search_documents: HybridSearchUseCase,
    answer_question: AnswerQuestionUseCase,
    recommend_folder: RecommendFolderUseCase,
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
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return RecommendFolderResponse.from_model(result)

    return router
