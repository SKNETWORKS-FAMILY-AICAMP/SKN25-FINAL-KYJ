from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from foldmind_ai_core.shared.types import Metadata


@dataclass(slots=True)
class SearchSort:
    field: str
    direction: str = "desc"


@dataclass(slots=True)
class SearchScope:
    document_type: str | None = None
    document_id: str | None = None
    document_ids: tuple[str, ...] = ()
    folder_ids: tuple[str, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None
    sort: SearchSort | None = None
    metadata_filter: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class RequestContext:
    tenant: str
    requested_at: str
    document_id: str | None = None
    folder_id: str | None = None
    metadata: Metadata = field(default_factory=dict)
