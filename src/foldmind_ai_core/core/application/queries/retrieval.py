from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(slots=True)
class TimestampRange:
    gt: str | None = None
    gte: str | None = None
    lt: str | None = None
    lte: str | None = None


@dataclass(slots=True)
class SearchSort:
    field: str
    direction: str = "desc"


@dataclass(slots=True)
class RequestContext:
    tenant: str
    requested_at: str
    document_id: str | None = None
    folder_id: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class SearchScope:
    document_type: str | None = None
    document_id: str | None = None
    document_ids: tuple[str, ...] = ()
    folder_ids: tuple[str, ...] = ()
    created_at: TimestampRange | None = None
    updated_at: TimestampRange | None = None
    sort: SearchSort | None = None
    metadata_filter: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class QueryAnchor:
    document_type: str | None
    document_id: str
    source_version: str | None = None


@dataclass(slots=True)
class RetrievalQuery:
    text: str
    request_context: RequestContext
    scope: SearchScope | None = None
    anchor: QueryAnchor | None = None


@dataclass(slots=True)
class FolderSearchQuery:
    tenant: str
    text: str
    scope: SearchScope | None = None
    excluded_folder_ids: tuple[str, ...] = ()
