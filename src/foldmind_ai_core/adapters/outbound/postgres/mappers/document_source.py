from __future__ import annotations

from typing import cast

from foldmind_ai_core.adapters.outbound.postgres.models.sources import DocumentSourceRow
from foldmind_ai_core.core.domain.models.document_sources import (
    DocumentSourceState,
)
from foldmind_ai_core.shared.types import JsonObject


def document_source_state_from_row(
    *,
    tenant: str,
    row: DocumentSourceRow,
) -> DocumentSourceState:
    return DocumentSourceState(
        tenant=tenant,
        document_type=row.document_type,
        document_id=row.document_id,
        source_version=row.source_version,
        title=row.title,
        created_at=_timestamp_text(row.source_created_at),
        updated_at=_timestamp_text(row.source_updated_at),
        content_digest=row.content_digest,
        content_size_bytes=row.content_size_bytes,
        metadata=_metadata_json_object(row.metadata_json),
    )


def _metadata_json_object(value: object) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata fields must contain JSON objects.")
    return cast(JsonObject, value)


def _timestamp_text(value: object) -> str:
    if value is None:
        return ""
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)
