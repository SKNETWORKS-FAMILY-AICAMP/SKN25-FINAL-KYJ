from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.execution.blocking_io import run_blocking
from foldmind_ai_core.core.application.ports.outbound.store.graph_store import GraphStore
from foldmind_ai_core.core.application.models.search import SearchScope


@dataclass(slots=True)
class RelationshipScopeResolver:
    graph: GraphStore

    async def document_search_scope(
        self,
        *,
        tenant: str,
        scope: SearchScope | None,
    ) -> SearchScope | None:
        if not self.relationship_scope_requested(scope):
            return scope
        if scope is None:
            return None
        document_ids = await run_blocking(
            self.graph.document_ids_for_scope,
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

    def relationship_scope_requested(self, scope: SearchScope | None) -> bool:
        return bool(scope and scope.folder_ids)

    def folder_scope_can_be_searched_directly(
        self,
        scope: SearchScope | None,
    ) -> bool:
        return bool(
            scope
            and scope.folder_ids
            and not scope.document_type
            and not scope.document_id
            and not scope.document_ids
            and not scope.metadata_filter
        )
