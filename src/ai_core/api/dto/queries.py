from __future__ import annotations

from typing import Any

from pydantic import Field

from ai_core.api.dto.base import APIBaseDTO
from ai_core.application.models.queries import AIQuery, QueryAnchor, RequestContext, SearchScope


class RequestContextDTO(APIBaseDTO):
    tenant: str
    user_id: str | None = None
    request_id: str | None = None
    locale: str | None = None
    timezone: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_model(self) -> RequestContext:
        return RequestContext(
            tenant=self.tenant,
            user_id=self.user_id,
            request_id=self.request_id,
            locale=self.locale,
            timezone=self.timezone,
            metadata=dict(self.metadata),
        )


class SearchScopeDTO(APIBaseDTO):
    entity_type: str | None = None
    entity_id: str | None = None
    folder_ids: tuple[str, ...] = Field(default_factory=tuple)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    metadata_filter: dict[str, Any] = Field(default_factory=dict)

    def to_model(self) -> SearchScope:
        return SearchScope(
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            folder_ids=self.folder_ids,
            tags=self.tags,
            metadata_filter=dict(self.metadata_filter),
        )


class QueryAnchorDTO(APIBaseDTO):
    entity_type: str
    entity_id: str
    source_key: str | None = None

    def to_model(self) -> QueryAnchor:
        return QueryAnchor(
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            source_key=self.source_key,
        )


class AIQueryDTO(APIBaseDTO):
    text: str
    request_context: RequestContextDTO
    scope: SearchScopeDTO | None = None
    anchor: QueryAnchorDTO | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    def to_model(self) -> AIQuery:
        return AIQuery(
            text=self.text,
            scope=self.scope.to_model() if self.scope else None,
            anchor=self.anchor.to_model() if self.anchor else None,
            request_context=self.request_context.to_model(),
            context=dict(self.context),
        )
