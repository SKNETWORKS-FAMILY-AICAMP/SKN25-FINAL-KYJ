from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO


class RequestContextDTO(APIDTO):
    tenant: str
    requested_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TimestampRangeDTO(APIDTO):
    gt: str | None = None
    gte: str | None = None
    lt: str | None = None
    lte: str | None = None


class SearchSortDTO(APIDTO):
    field: Literal["created_at", "updated_at"]
    direction: Literal["asc", "desc"] = "desc"


class SearchScopeDTO(APIDTO):
    document_type: str | None = None
    document_id: str | None = None
    document_ids: tuple[str, ...] = Field(default_factory=tuple)
    folder_ids: tuple[str, ...] = Field(default_factory=tuple)
    created_at: TimestampRangeDTO | None = None
    updated_at: TimestampRangeDTO | None = None
    sort: SearchSortDTO | None = None
    metadata_filter: dict[str, Any] = Field(default_factory=dict)


class QueryAnchorDTO(APIDTO):
    document_type: str | None = None
    document_id: str
    source_version: str | None = None


class RetrievalQueryDTO(APIDTO):
    text: str
    request_context: RequestContextDTO
    scope: SearchScopeDTO | None = None
    anchor: QueryAnchorDTO | None = None
