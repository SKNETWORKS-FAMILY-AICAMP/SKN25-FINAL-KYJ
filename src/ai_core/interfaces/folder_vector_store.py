from __future__ import annotations

from typing import Protocol

from ai_core.common.types import Vector
from ai_core.schemas.indexed import IndexedFolder
from ai_core.schemas.retrieval import FolderRetrievalResult


class FolderVectorStore(Protocol):
    def upsert(self, folders: list[IndexedFolder], vectors: list[Vector]) -> None:
        """Insert or update vectors for folders."""

    def delete(self, *, tenant: str, folder_id: str) -> None:
        """Delete all vectors for a folder."""

    def similarity_search(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
    ) -> list[FolderRetrievalResult]:
        """Return top-k relevant folders for the query."""
