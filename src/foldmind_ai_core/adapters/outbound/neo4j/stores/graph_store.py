from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    delete_document_projection,
    delete_folder_signal_projection,
    delete_folder_projection,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_document_projection as run_replace_document_projection,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_document_folder_relations as run_replace_document_folder_relations,
)
from foldmind_ai_core.adapters.outbound.neo4j.projection import (
    replace_folder_projection as run_replace_folder_projection,
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
from foldmind_ai_core.core.application.projections.graph import (
    DocumentFolderRelationProjection,
    DocumentRelationshipProjection,
    DocumentSignalProjection,
    FolderRelationshipProjection,
    FolderSignalProjection,
)
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.domain.models.retrieval.results import (
    DocumentRetrievalResult,
    RetrievedFolder,
)


@dataclass(slots=True)
class Neo4jGraphStore:
    client: Any

    def replace_document_projection(
        self,
        *,
        relationships: DocumentRelationshipProjection,
        signals: DocumentSignalProjection,
    ) -> None:
        with self.client.session() as session:
            _execute_write(
                session,
                lambda tx: run_replace_document_projection(
                    tx,
                    relationships=relationships,
                    signals=signals,
                ),
            )

    def replace_document_folder_relations(
        self,
        *,
        projection: DocumentFolderRelationProjection,
    ) -> None:
        with self.client.session() as session:
            _execute_write(
                session,
                lambda tx: run_replace_document_folder_relations(
                    tx,
                    projection=projection,
                ),
            )

    def replace_folder_projection(
        self,
        *,
        relationships: FolderRelationshipProjection,
        signals: FolderSignalProjection,
    ) -> None:
        with self.client.session() as session:
            _execute_write(
                session,
                lambda tx: run_replace_folder_projection(
                    tx,
                    relationships=relationships,
                    signals=signals,
                ),
            )

    def document_ids_for_scope(
        self,
        *,
        tenant: str,
        scope: SearchScope,
    ) -> tuple[str, ...]:
        with self.client.session() as session:
            return run_document_ids_for_scope(session, tenant=tenant, scope=scope)

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        with self.client.session() as session:
            return run_folders_for_documents(
                session,
                tenant=tenant,
                document_ids=document_ids,
            )

    def delete_document(
        self,
        *,
        document_id: str,
    ) -> None:
        with self.client.session() as session:
            _execute_write(
                session,
                lambda tx: delete_document_projection(
                    tx,
                    document_id=document_id,
                ),
            )

    def delete_folder_signals(self, *, folder_id: str) -> None:
        with self.client.session() as session:
            _execute_write(
                session,
                lambda tx: delete_folder_signal_projection(
                    tx,
                    folder_id=folder_id,
                ),
            )

    def delete_folder(self, *, folder_id: str) -> None:
        with self.client.session() as session:
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
        with self.client.session() as session:
            return run_graph_search(
                session,
                tenant=tenant,
                query_text=query_text,
                top_k=top_k,
                scope=scope,
            )


def _execute_write(session: Any, operation: Callable[[Any], None]) -> None:
    if hasattr(session, "execute_write"):
        session.execute_write(operation)
        return
    operation(session)
