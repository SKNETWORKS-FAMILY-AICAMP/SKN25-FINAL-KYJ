from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from foldmind_ai_core.bootstrap.app_factory import create_app
from foldmind_ai_core.bootstrap.container.dependencies import (
    AICapabilities,
    ApplicationDependencies,
    ApplicationStorage,
)
from foldmind_ai_core.bootstrap.container.providers import (
    build_ai_capabilities,
    build_prompt_store,
)
from foldmind_ai_core.bootstrap.container.storage import build_application_storage
from foldmind_ai_core.bootstrap.container.use_cases import build_use_cases
from foldmind_ai_core.bootstrap.settings import APISettings
from foldmind_ai_core.core.application.ports.outbound.prompt_store import PromptStore
from foldmind_ai_core.core.application.services.document_retrieval_policy import (
    DocumentRetrievalConfig,
)


def build_app(
    dependencies: ApplicationDependencies,
    *,
    settings: APISettings | None = None,
    document_retrieval_config: DocumentRetrievalConfig | None = None,
    workflow_checkpointer: Any | None = None,
) -> FastAPI:
    settings = settings or APISettings()
    return create_app(
        build_use_cases(
            dependencies,
            settings=settings,
            document_retrieval_config=document_retrieval_config,
            workflow_checkpointer=workflow_checkpointer,
        ),
        settings=settings,
    )


def build_configured_app(
    *,
    settings: APISettings | None = None,
    storage: ApplicationStorage | None = None,
    ai_capabilities: AICapabilities | None = None,
    prompt_store: PromptStore | None = None,
    document_retrieval_config: DocumentRetrievalConfig | None = None,
    workflow_checkpointer: Any | None = None,
) -> FastAPI:
    settings = settings or APISettings()
    ai_capabilities = ai_capabilities or build_ai_capabilities(settings)
    storage = storage or build_application_storage(settings)
    prompts = prompt_store or build_prompt_store(settings)
    return build_app(
        ApplicationDependencies(
            ai=ai_capabilities,
            storage=storage,
            prompt_store=prompts,
        ),
        settings=settings,
        document_retrieval_config=document_retrieval_config,
        workflow_checkpointer=workflow_checkpointer,
    )
