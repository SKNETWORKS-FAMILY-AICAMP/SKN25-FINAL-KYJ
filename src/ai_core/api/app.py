from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_core.api.routes import create_indexing_router, create_retrieval_router, create_tasks_router
from ai_core.api.settings import APISettings
from ai_core.application.use_cases.answer_question import AnswerQuestionUseCase
from ai_core.application.use_cases.delete_document_index import DeleteDocumentIndexUseCase
from ai_core.application.use_cases.hybrid_search import HybridSearchUseCase
from ai_core.application.use_cases.index_document import IndexDocumentUseCase
from ai_core.application.use_cases.recommend_folder import RecommendFolderUseCase
from ai_core.application.use_cases.record_action_result import RecordActionResultUseCase
from ai_core.application.use_cases.run_task import RunTaskUseCase


@dataclass(slots=True)
class APIUseCases:
    index_document: IndexDocumentUseCase
    delete_document_index: DeleteDocumentIndexUseCase
    run_task: RunTaskUseCase
    record_action_result: RecordActionResultUseCase
    search_documents: HybridSearchUseCase
    answer_question: AnswerQuestionUseCase
    recommend_folder: RecommendFolderUseCase


def create_app(
    use_cases: APIUseCases,
    *,
    settings: APISettings | None = None,
) -> FastAPI:
    settings = settings or APISettings()
    app = FastAPI(title=settings.title, version=settings.version)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=settings.cors_allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(
        create_indexing_router(
            index_document=use_cases.index_document,
            delete_document_index=use_cases.delete_document_index,
        )
    )
    app.include_router(
        create_retrieval_router(
            search_documents=use_cases.search_documents,
            answer_question=use_cases.answer_question,
            recommend_folder=use_cases.recommend_folder,
        )
    )
    app.include_router(
        create_tasks_router(
            run_task=use_cases.run_task,
            record_action_result=use_cases.record_action_result,
        )
    )
    return app
