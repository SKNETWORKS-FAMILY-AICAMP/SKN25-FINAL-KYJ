from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from foldmind_ai_core.adapters.inbound.http.routers.indexing import create_indexing_router
from foldmind_ai_core.adapters.inbound.http.routers.tasks import create_tasks_router
from foldmind_ai_core.bootstrap.api_use_cases import APIUseCases

if TYPE_CHECKING:
    from foldmind_ai_core.bootstrap.settings import APISettings


def create_app(
    use_cases: APIUseCases,
    *,
    settings: APISettings | None = None,
) -> FastAPI:
    if settings is None:
        from foldmind_ai_core.bootstrap.settings import APISettings

        settings = APISettings()
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
            update_document_folder_relations=use_cases.update_document_folder_relations,
            index_folder=use_cases.index_folder,
            delete_folder_index=use_cases.delete_folder_index,
        )
    )
    app.include_router(
        create_tasks_router(
            run_task=use_cases.run_task,
            get_task=use_cases.get_task,
            remove_task_input=use_cases.remove_task_input,
            record_action_result=use_cases.record_action_result,
        )
    )
    return app
