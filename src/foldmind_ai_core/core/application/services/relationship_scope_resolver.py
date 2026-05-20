from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.ports.outbound.graph_store import GraphStore
from foldmind_ai_core.core.application.queries.retrieval import SearchScope


@dataclass(slots=True)
class RelationshipScopeResolver:
    graph: GraphStore

    def document_search_scope(
        self,
        *,
        tenant: str,
        scope: SearchScope | None,
    ) -> SearchScope | None:
        if not relationship_scope_requested(scope):
            return scope
        document_ids = self.graph.document_ids_for_scope(
            tenant=tenant,
            scope=scope,
        )
        if not document_ids:
            return None
        return SearchScope(
            document_type=scope.document_type,
            document_id=None,
            document_ids=document_ids,
            created_at=scope.created_at,
            updated_at=scope.updated_at,
            sort=scope.sort,
            metadata_filter=dict(scope.metadata_filter),
        )


def relationship_scope_requested(scope: SearchScope | None) -> bool:
    return bool(scope and scope.folder_ids)
