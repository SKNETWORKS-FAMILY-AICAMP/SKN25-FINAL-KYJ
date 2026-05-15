from __future__ import annotations

from typing import Any

from pydantic import Field

from foldmind_ai_core.adapters.inbound.http.schemas.base import APIBaseDTO
from foldmind_ai_core.domain.retrieval.queries import (
    AIQuery,
    QueryAnchor,
    RequestContext,
    SearchScope,
)
from foldmind_ai_core.shared.validation import (
    require_non_blank,
    require_optional_non_blank,
    require_optional_uuid,
    require_uuid,
    require_uuid_items,
)


class RequestContextDTO(APIBaseDTO):
    tenant: str
    locale: str | None = None
    timezone: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_model(self) -> RequestContext:
        require_non_blank(self.tenant, "tenant")
        return RequestContext(
            tenant=self.tenant,
            locale=self.locale,
            timezone=self.timezone,
            metadata=dict(self.metadata),
        )


class SearchScopeDTO(APIBaseDTO):
    document_type: str | None = None
    document_id: str | None = None
    document_ids: tuple[str, ...] = Field(default_factory=tuple)
    folder_ids: tuple[str, ...] = Field(default_factory=tuple)
    tag_ids: tuple[str, ...] = Field(default_factory=tuple)
    metadata_filter: dict[str, Any] = Field(default_factory=dict)

    def to_model(self) -> SearchScope:
        require_optional_non_blank(self.document_type, "document_type")
        require_optional_uuid(self.document_id, "document_id")
        require_uuid_items(self.document_ids, "document_ids")
        require_uuid_items(self.folder_ids, "folder_ids")
        require_uuid_items(self.tag_ids, "tag_ids")
        return SearchScope(
            document_type=self.document_type,
            document_id=self.document_id,
            document_ids=self.document_ids,
            folder_ids=self.folder_ids,
            tag_ids=self.tag_ids,
            metadata_filter=dict(self.metadata_filter),
        )


class QueryAnchorDTO(APIBaseDTO):
    document_type: str
    document_id: str
    source_version: str | None = None

    def to_model(self) -> QueryAnchor:
        require_non_blank(self.document_type, "document_type")
        require_uuid(self.document_id, "document_id")
        require_optional_non_blank(self.source_version, "source_version")
        return QueryAnchor(
            document_type=self.document_type,
            document_id=self.document_id,
            source_version=self.source_version,
        )


class AIQueryDTO(APIBaseDTO):
    text: str
    request_context: RequestContextDTO
    scope: SearchScopeDTO | None = None
    anchor: QueryAnchorDTO | None = None

    def to_model(self) -> AIQuery:
        require_non_blank(self.text, "text")
        return AIQuery(
            text=self.text,
            scope=self.scope.to_model() if self.scope else None,
            anchor=self.anchor.to_model() if self.anchor else None,
            request_context=self.request_context.to_model(),
        )
