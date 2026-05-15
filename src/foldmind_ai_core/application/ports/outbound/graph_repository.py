from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.domain.knowledge_graph.models import (
    DocumentConceptProjection,
    DocumentRelationshipProjection,
    FolderRelationshipProjection,
    TagProjection,
)
from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import (
    DocumentRetrievalResult,
    RetrievedFolder,
)


class GraphRepository(Protocol):
    def replace_document_projection(
        self,
        *,
        relationships: DocumentRelationshipProjection,
        concepts: DocumentConceptProjection,
    ) -> None:
        ...

    def replace_folder_hierarchy(self, projection: FolderRelationshipProjection) -> None:
        ...

    def upsert_tag(self, projection: TagProjection) -> None:
        ...

    def document_ids_for_scope(
        self,
        *,
        tenant: str,
        scope: SearchScope,
    ) -> tuple[str, ...]:
        ...

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        ...

    def delete_document(self, *, document_id: str) -> None:
        ...

    def delete_folder(self, *, folder_id: str) -> None:
        ...

    def graph_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        """Return document candidates discovered through graph relationships."""
        ...
