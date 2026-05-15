from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.ports.outbound.graph_repository import GraphRepository
from foldmind_ai_core.domain.retrieval.queries import SearchScope


@dataclass(slots=True)
class RelationshipScopeResolver:
    graph: GraphRepository

    def document_search_scope(
        self,
        *,
        tenant: str,
        scope: SearchScope | None,
    ) -> SearchScope | None:
        if scope is None or not relationship_scope_requested(scope):
            return scope
        document_ids = self.graph.document_ids_for_scope(
            tenant=tenant,
            scope=scope,
        )
        if not document_ids:
            return None
        return SearchScope(
            document_type=scope.document_type,
            document_id=scope.document_id,
            document_ids=document_ids,
            metadata_filter=dict(scope.metadata_filter),
        )


def relationship_scope_requested(scope: SearchScope | None) -> bool:
    return bool(scope is not None and (scope.folder_ids or scope.tag_ids))
