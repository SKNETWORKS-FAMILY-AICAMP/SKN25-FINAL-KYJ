"""FastAPI route factories."""

from ai_core.api.routes.indexing import create_indexing_router
from ai_core.api.routes.retrieval import create_retrieval_router
from ai_core.api.routes.tasks import create_tasks_router

__all__ = [
    "create_indexing_router",
    "create_retrieval_router",
    "create_tasks_router",
]
