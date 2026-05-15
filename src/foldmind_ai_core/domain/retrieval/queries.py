from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(slots=True)
class RequestContext:
    tenant: str
    locale: str | None = None
    timezone: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class SearchScope:
    document_type: str | None = None
    document_id: str | None = None
    document_ids: tuple[str, ...] = ()
    folder_ids: tuple[str, ...] = ()
    tag_ids: tuple[str, ...] = ()
    metadata_filter: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class QueryAnchor:
    document_type: str
    document_id: str
    source_version: str | None = None


@dataclass(slots=True)
class AIQuery:
    text: str
    request_context: RequestContext
    scope: SearchScope | None = None
    anchor: QueryAnchor | None = None
