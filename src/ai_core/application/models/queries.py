from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_core.common.types import Metadata


@dataclass(slots=True)
class RequestContext:
    tenant: str
    user_id: str | None = None
    request_id: str | None = None
    locale: str | None = None
    timezone: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class SearchScope:
    entity_type: str | None = None
    entity_id: str | None = None
    folder_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata_filter: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class QueryAnchor:
    entity_type: str
    entity_id: str
    source_key: str | None = None


@dataclass(slots=True)
class AIQuery:
    text: str
    scope: SearchScope | None = None
    anchor: QueryAnchor | None = None
    request_context: RequestContext | None = None
    context: dict[str, Any] = field(default_factory=dict)
