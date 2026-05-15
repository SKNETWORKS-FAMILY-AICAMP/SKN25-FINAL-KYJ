from __future__ import annotations

from foldmind_ai_core.bootstrap.container.checkpointing import (
    build_postgres_workflow_checkpointer,
    build_workflow_checkpointer,
)
from foldmind_ai_core.bootstrap.container.dependencies import (
    AICoreDependencies,
    AIProviderAdapters,
    OutboxProjectionRepositories,
    OutboxProjectionRepositoryAdapter,
    RepositoryAdapter,
)
from foldmind_ai_core.bootstrap.container.outbox import (
    build_outbox_dispatcher,
    build_outbox_worker,
)
from foldmind_ai_core.bootstrap.container.providers import (
    build_ai_provider,
    build_prompt_repository,
    default_prompt_root,
)
from foldmind_ai_core.bootstrap.container.repositories import (
    build_outbox_projection_repository_adapter,
    build_repository_adapter,
)
from foldmind_ai_core.bootstrap.container.use_cases import (
    build_app,
    build_configured_app,
    build_use_cases,
)

__all__ = [
    "AICoreDependencies",
    "AIProviderAdapters",
    "OutboxProjectionRepositories",
    "OutboxProjectionRepositoryAdapter",
    "RepositoryAdapter",
    "build_ai_provider",
    "build_app",
    "build_configured_app",
    "build_outbox_dispatcher",
    "build_outbox_projection_repository_adapter",
    "build_outbox_worker",
    "build_postgres_workflow_checkpointer",
    "build_prompt_repository",
    "build_repository_adapter",
    "build_use_cases",
    "build_workflow_checkpointer",
    "default_prompt_root",
]
