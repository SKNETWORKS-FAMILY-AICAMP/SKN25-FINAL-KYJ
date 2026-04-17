from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchScope:
    entity_type: str | None = None
    entity_id: str | None = None


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
    context: dict[str, Any] = field(default_factory=dict)
