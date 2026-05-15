from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.services.folder_retrieval_service import (
    FolderRetrievalService,
)
from foldmind_ai_core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
    relationship_scope_requested,
)
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.retrieval.queries import AIQuery, SearchScope
from foldmind_ai_core.domain.retrieval.results import FolderRetrievalResult


@dataclass(slots=True)
class FindFoldersUseCase:
    retrieval: FolderRetrievalService
    scope_resolver: RelationshipScopeResolver

    def execute(self, request: SourceDocument | AIQuery) -> list[FolderRetrievalResult]:
        query = _folder_query(request)
        document_search_scope = self.scope_resolver.document_search_scope(
            tenant=query.tenant,
            scope=query.scope,
        )
        if document_search_scope is None and relationship_scope_requested(query.scope):
            return []
        return self.retrieval.search(
            tenant=query.tenant,
            text=query.text,
            scope=query.scope,
            document_search_scope=document_search_scope,
            excluded_folder_ids=query.excluded_folder_ids,
        )


@dataclass(slots=True)
class _FolderQuery:
    tenant: str
    text: str
    scope: SearchScope | None = None
    excluded_folder_ids: tuple[str, ...] = ()


def _folder_query(request: SourceDocument | AIQuery) -> _FolderQuery:
    if isinstance(request, AIQuery):
        return _FolderQuery(
            tenant=request.request_context.tenant,
            text=request.text,
            scope=request.scope,
        )
    return _FolderQuery(
        tenant=request.tenant,
        text=request.full_text,
        excluded_folder_ids=request.folder_ids,
    )
