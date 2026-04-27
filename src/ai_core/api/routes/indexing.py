from __future__ import annotations

from typing import Any


def create_indexing_router() -> Any:
    try:
        from fastapi import APIRouter
    except ModuleNotFoundError as exc:
        raise RuntimeError("Install foldmind-ai-core[api] to use FastAPI routes.") from exc

    router = APIRouter(prefix="/indexing", tags=["indexing"])
    return router
