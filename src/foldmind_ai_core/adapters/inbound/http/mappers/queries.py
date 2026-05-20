from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.dtos.queries import (
    QueryAnchorDTO,
    RequestContextDTO,
    RetrievalQueryDTO,
    SearchScopeDTO,
    TimestampRangeDTO,
)
from foldmind_ai_core.core.application.queries.retrieval import (
    QueryAnchor,
    RequestContext,
    RetrievalQuery,
    SearchScope,
    SearchSort,
    TimestampRange,
)
from foldmind_ai_core.shared.validation import (
    require_non_blank,
    require_optional_non_blank,
    require_optional_uuid,
    require_aware_iso_timestamp,
    require_uuid,
    require_uuid_items,
    resolve_requested_at,
)


def request_context_from_dto(dto: RequestContextDTO) -> RequestContext:
    return RequestContext(
        tenant=require_non_blank(dto.tenant, "tenant"),
        requested_at=resolve_requested_at(dto.requested_at),
        metadata=dict(dto.metadata),
    )


def search_scope_from_dto(dto: SearchScopeDTO) -> SearchScope:
    return SearchScope(
        document_type=require_optional_non_blank(dto.document_type, "document_type"),
        document_id=require_optional_uuid(dto.document_id, "document_id"),
        document_ids=require_uuid_items(dto.document_ids, "document_ids"),
        folder_ids=require_uuid_items(dto.folder_ids, "folder_ids"),
        created_at=timestamp_range_from_dto(dto.created_at, "created_at"),
        updated_at=timestamp_range_from_dto(dto.updated_at, "updated_at"),
        sort=(
            SearchSort(field=dto.sort.field, direction=dto.sort.direction)
            if dto.sort is not None
            else None
        ),
        metadata_filter=dict(dto.metadata_filter),
    )


def timestamp_range_from_dto(
    dto: TimestampRangeDTO | None,
    field_name: str,
) -> TimestampRange | None:
    if dto is None:
        return None
    return TimestampRange(
        gt=(
            require_aware_iso_timestamp(dto.gt, f"{field_name}.gt")
            if dto.gt is not None
            else None
        ),
        gte=(
            require_aware_iso_timestamp(dto.gte, f"{field_name}.gte")
            if dto.gte is not None
            else None
        ),
        lt=(
            require_aware_iso_timestamp(dto.lt, f"{field_name}.lt")
            if dto.lt is not None
            else None
        ),
        lte=(
            require_aware_iso_timestamp(dto.lte, f"{field_name}.lte")
            if dto.lte is not None
            else None
        ),
    )


def query_anchor_from_dto(dto: QueryAnchorDTO) -> QueryAnchor:
    return QueryAnchor(
        document_type=require_optional_non_blank(dto.document_type, "document_type"),
        document_id=require_uuid(dto.document_id, "document_id"),
        source_version=require_optional_non_blank(
            dto.source_version,
            "source_version",
        ),
    )


def retrieval_query_from_dto(dto: RetrievalQueryDTO) -> RetrievalQuery:
    require_non_blank(dto.text, "text")
    return RetrievalQuery(
        text=dto.text,
        request_context=request_context_from_dto(dto.request_context),
        scope=search_scope_from_dto(dto.scope) if dto.scope is not None else None,
        anchor=query_anchor_from_dto(dto.anchor) if dto.anchor is not None else None,
    )
