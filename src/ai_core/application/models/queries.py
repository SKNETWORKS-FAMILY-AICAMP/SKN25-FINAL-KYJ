from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_core.common.types import Metadata
from ai_core.common.validation import (
    require_non_blank,
    require_non_blank_items,
    require_optional_non_blank,
)


@dataclass(slots=True)
class RequestContext:
    tenant: str
    user_id: str | None = None
    request_id: str | None = None
    locale: str | None = None
    timezone: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_blank(self.tenant, "tenant")
        require_optional_non_blank(self.user_id, "user_id")
        require_optional_non_blank(self.request_id, "request_id")


@dataclass(slots=True)
class SearchScope:
    entity_type: str | None = None
    entity_id: str | None = None
    folder_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata_filter: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_optional_non_blank(self.entity_type, "entity_type")
        require_optional_non_blank(self.entity_id, "entity_id")
        require_non_blank_items(self.folder_ids, "folder_ids")
        require_non_blank_items(self.tags, "tags")


@dataclass(slots=True)
class QueryAnchor:
    entity_type: str
    entity_id: str
    source_key: str | None = None

    def __post_init__(self) -> None:
        require_non_blank(self.entity_type, "entity_type")
        require_non_blank(self.entity_id, "entity_id")
        require_optional_non_blank(self.source_key, "source_key")


@dataclass(slots=True)
class AIQuery:
    text: str
    scope: SearchScope | None = None
    anchor: QueryAnchor | None = None
    request_context: RequestContext | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_blank(self.text, "text")
