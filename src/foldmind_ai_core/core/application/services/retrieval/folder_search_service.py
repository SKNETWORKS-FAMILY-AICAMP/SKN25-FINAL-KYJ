from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.models.retrieval import (
    FolderRetrievalResult,
    FolderSearchQuery,
)
from foldmind_ai_core.core.application.services.retrieval.folder_retrieval_service import (
    FolderRetrievalService,
)
from foldmind_ai_core.core.application.services.retrieval.scope_resolver import (
    RelationshipScopeResolver,
)


@dataclass(slots=True)
class FolderSearchService:
    retrieval: FolderRetrievalService
    scope_resolver: RelationshipScopeResolver

    async def search(self, query: FolderSearchQuery) -> tuple[FolderRetrievalResult, ...]:
        if not query.text.strip():
            return ()
        document_search_scope = await self.scope_resolver.document_search_scope(
            tenant=query.tenant,
            scope=query.scope,
        )
        document_scope_has_no_matches = (
            document_search_scope is None
            and self.scope_resolver.relationship_scope_requested(query.scope)
        )
        if (
            document_scope_has_no_matches
            and not self.scope_resolver.folder_scope_can_be_searched_directly(
                query.scope
            )
        ):
            return ()
        return tuple(
            await self.retrieval.search(
                tenant=query.tenant,
                text=query.text,
                scope=query.scope,
                document_search_scope=document_search_scope,
                include_document_signals=not document_scope_has_no_matches,
                excluded_folder_ids=query.excluded_folder_ids,
            )
        )
