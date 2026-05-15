from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from foldmind_ai_core.adapters.inbound.http.routers.indexing import create_indexing_router
from foldmind_ai_core.adapters.inbound.http.routers.retrieval import create_retrieval_router
from foldmind_ai_core.adapters.inbound.http.routers.tasks import create_tasks_router
from foldmind_ai_core.application.ports.inbound.indexing_use_case import (
    DeleteDocumentIndexUseCasePort,
    DeleteFolderIndexUseCasePort,
    IndexDocumentUseCasePort,
    IndexFolderUseCasePort,
)
from foldmind_ai_core.application.ports.inbound.recommendation_use_case import (
    RecommendFolderUseCasePort,
)
from foldmind_ai_core.application.ports.inbound.retrieval_use_case import (
    AnswerQuestionUseCasePort,
    SearchDocumentsUseCasePort,
)
from foldmind_ai_core.application.ports.inbound.workflow_use_case import (
    GetTaskUseCasePort,
    RecordActionResultUseCasePort,
    RemoveTaskRequestUseCasePort,
    RunTaskUseCasePort,
)
from foldmind_ai_core.bootstrap.settings import APISettings


@dataclass(slots=True)
class APIUseCases:
    index_document: IndexDocumentUseCasePort
    delete_document_index: DeleteDocumentIndexUseCasePort
    index_folder: IndexFolderUseCasePort
    delete_folder_index: DeleteFolderIndexUseCasePort
    run_task: RunTaskUseCasePort
    get_task: GetTaskUseCasePort
    remove_task_request: RemoveTaskRequestUseCasePort
    record_action_result: RecordActionResultUseCasePort
    search_documents: SearchDocumentsUseCasePort
    answer_question: AnswerQuestionUseCasePort
    recommend_folder: RecommendFolderUseCasePort


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
            index_folder=use_cases.index_folder,
            delete_folder_index=use_cases.delete_folder_index,
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
            get_task=use_cases.get_task,
            remove_task_request=use_cases.remove_task_request,
            record_action_result=use_cases.record_action_result,
        )
    )
    return app
