from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.services.use_case_contracts import RetrievalResultFilter
from foldmind_ai_core.application.services.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
    relationship_scope_requested,
)
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.retrieval.results import RetrievalResult


@dataclass(slots=True)
class FindDocumentsUseCase:
    retrieval: DocumentRetrievalService
    scope_resolver: RelationshipScopeResolver
    result_filter: RetrievalResultFilter | None = None

    def execute(
        self,
        query: AIQuery,
        *,
        require_comprehensive_search: bool = False,
    ) -> list[RetrievalResult]:
        tenant = query.request_context.tenant
        resolved_scope = self.scope_resolver.document_search_scope(
            tenant=tenant,
            scope=query.scope,
        )
        if resolved_scope is None and relationship_scope_requested(query.scope):
            return []

        if query.scope is not resolved_scope:
            query = AIQuery(
                text=query.text,
                request_context=query.request_context,
                scope=resolved_scope,
                anchor=query.anchor,
            )
        results = self.retrieval.search(
            tenant=tenant,
            query=query,
            comprehensive=require_comprehensive_search,
        )
        if self.result_filter is None:
            return results
        return self.result_filter.filter(query=query, results=results)
