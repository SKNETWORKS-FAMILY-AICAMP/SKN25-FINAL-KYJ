from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.models.retrieval import (
    RetrievalQuery,
    RetrievalResult,
)
from foldmind_ai_core.core.application.services.retrieval.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.core.application.services.retrieval.scope_resolver import (
    RelationshipScopeResolver,
)


@dataclass(slots=True)
class DocumentSearchService:
    retrieval: DocumentRetrievalService
    scope_resolver: RelationshipScopeResolver

    async def search(
        self,
        query: RetrievalQuery,
        *,
        require_comprehensive_search: bool = False,
    ) -> tuple[RetrievalResult, ...]:
        if not query.text.strip():
            return ()
        tenant = query.request_context.tenant
        resolved_scope = await self.scope_resolver.document_search_scope(
            tenant=tenant,
            scope=query.scope,
        )
        if (
            resolved_scope is None
            and self.scope_resolver.relationship_scope_requested(query.scope)
        ):
            return ()

        if query.scope is not resolved_scope:
            query = RetrievalQuery(
                text=query.text,
                request_context=query.request_context,
                scope=resolved_scope,
            )
        results = await self.retrieval.search(
            tenant=tenant,
            query=query,
            comprehensive=require_comprehensive_search,
        )
        return tuple(results)
