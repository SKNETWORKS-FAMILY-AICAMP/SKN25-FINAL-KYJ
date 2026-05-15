from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from foldmind_ai_core.adapters.outbound.neo4j.client import Neo4jClient
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    delete_document_projection,
    delete_folder_projection,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_document_concepts as run_replace_document_concepts,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_document_projection as run_replace_document_projection,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_document_relationships as run_replace_document_relationships,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_folder_hierarchy as run_replace_folder_hierarchy,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    upsert_tag as run_upsert_tag,
)
from foldmind_ai_core.adapters.outbound.neo4j.search import (
    document_ids_for_scope as run_document_ids_for_scope,
)
from foldmind_ai_core.adapters.outbound.neo4j.search import (
    folders_for_documents as run_folders_for_documents,
)
from foldmind_ai_core.adapters.outbound.neo4j.search import (
    graph_search as run_graph_search,
)
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


@dataclass(slots=True)
class Neo4jGraphRepository:
    client: Neo4jClient

    def replace_document_projection(
        self,
        *,
        relationships: DocumentRelationshipProjection,
        concepts: DocumentConceptProjection,
    ) -> None:
        with self._session() as session:
            _execute_write(
                session,
                lambda tx: run_replace_document_projection(
                    tx,
                    relationships=relationships,
                    concepts=concepts,
                ),
            )

    def replace_document_relationships(
        self,
        projection: DocumentRelationshipProjection,
    ) -> None:
        with self._session() as session:
            _execute_write(
                session,
                lambda tx: run_replace_document_relationships(tx, projection),
            )

    def replace_document_concepts(self, projection: DocumentConceptProjection) -> None:
        with self._session() as session:
            _execute_write(
                session,
                lambda tx: run_replace_document_concepts(tx, projection),
            )

    def replace_folder_hierarchy(self, projection: FolderRelationshipProjection) -> None:
        with self._session() as session:
            _execute_write(
                session,
                lambda tx: run_replace_folder_hierarchy(tx, projection),
            )

    def upsert_tag(self, projection: TagProjection) -> None:
        with self._session() as session:
            _execute_write(session, lambda tx: run_upsert_tag(tx, projection))

    def document_ids_for_scope(
        self,
        *,
        tenant: str,
        scope: SearchScope,
    ) -> tuple[str, ...]:
        with self._session() as session:
            return run_document_ids_for_scope(session, tenant=tenant, scope=scope)

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        with self._session() as session:
            return run_folders_for_documents(
                session,
                tenant=tenant,
                document_ids=document_ids,
            )

    def delete_document(self, *, document_id: str) -> None:
        with self._session() as session:
            _execute_write(
                session,
                lambda tx: delete_document_projection(
                    tx,
                    document_id=document_id,
                ),
            )

    def delete_folder(self, *, folder_id: str) -> None:
        with self._session() as session:
            _execute_write(
                session,
                lambda tx: delete_folder_projection(
                    tx,
                    folder_id=folder_id,
                ),
            )

    def graph_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        with self._session() as session:
            return run_graph_search(
                session,
                tenant=tenant,
                query_text=query_text,
                top_k=top_k,
                scope=scope,
            )

    def _session(self) -> Any:
        return self.client.session()


def _execute_write(session: Any, operation: Callable[[Any], None]) -> None:
    if hasattr(session, "execute_write"):
        session.execute_write(lambda tx: operation(tx))
        return
    operation(session)
