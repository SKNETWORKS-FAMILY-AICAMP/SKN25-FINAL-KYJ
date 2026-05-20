from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.factories.retrieval_results import (
    search_folders_result_from_domain,
)
from foldmind_ai_core.core.application.results.retrieval import SearchFoldersResult
from foldmind_ai_core.core.application.services.folder_retrieval_service import (
    FolderRetrievalService,
)
from foldmind_ai_core.core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
    relationship_scope_requested,
)
from foldmind_ai_core.core.application.queries.retrieval import FolderSearchQuery


@dataclass(slots=True)
class FindFoldersUseCase:
    retrieval: FolderRetrievalService
    scope_resolver: RelationshipScopeResolver

    def execute(self, query: FolderSearchQuery) -> SearchFoldersResult:
        if not query.text.strip():
            return SearchFoldersResult(results=())
        document_search_scope = self.scope_resolver.document_search_scope(
            tenant=query.tenant,
            scope=query.scope,
        )
        document_scope_has_no_matches = (
            document_search_scope is None and relationship_scope_requested(query.scope)
        )
        can_search_folder_scope = bool(
            query.scope
            and query.scope.folder_ids
            and not query.scope.document_type
            and not query.scope.document_id
            and not query.scope.document_ids
            and not query.scope.metadata_filter
        )
        if document_scope_has_no_matches and not can_search_folder_scope:
            return SearchFoldersResult(results=())
        return search_folders_result_from_domain(
            self.retrieval.search(
                tenant=query.tenant,
                text=query.text,
                scope=query.scope,
                document_search_scope=document_search_scope,
                include_document_signals=not document_scope_has_no_matches,
                excluded_folder_ids=query.excluded_folder_ids,
            )
        )
