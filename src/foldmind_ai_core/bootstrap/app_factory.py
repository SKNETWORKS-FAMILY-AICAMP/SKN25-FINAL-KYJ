from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from foldmind_ai_core.adapters.inbound.http.routers.indexing import create_indexing_router
from foldmind_ai_core.adapters.inbound.http.routers.tasks import create_tasks_router
from foldmind_ai_core.bootstrap.api_services import APIApplicationServices

if TYPE_CHECKING:
    from foldmind_ai_core.bootstrap.settings import APISettings


def create_app(
    application_services: APIApplicationServices,
    *,
    settings: APISettings | None = None,
    shutdown_callbacks: tuple[Callable[[], Awaitable[None]], ...] = (),
) -> FastAPI:
    if settings is None:
        from foldmind_ai_core.bootstrap.settings import APISettings

        settings = APISettings()
    lifespan = _lifespan(shutdown_callbacks) if shutdown_callbacks else None
    app = FastAPI(title=settings.title, version=settings.version, lifespan=lifespan)

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
            document_indexing=application_services.document_indexing,
            folder_indexing=application_services.folder_indexing,
        )
    )
    app.include_router(
        create_tasks_router(
            task_workflow=application_services.task_workflow,
        )
    )
    return app


def _lifespan(
    shutdown_callbacks: tuple[Callable[[], Awaitable[None]], ...],
) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            for callback in shutdown_callbacks:
                await callback()

    return lifespan
