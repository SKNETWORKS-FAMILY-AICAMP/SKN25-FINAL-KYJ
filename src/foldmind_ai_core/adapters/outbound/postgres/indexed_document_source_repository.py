from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient, row_value
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.shared.types import JsonObject

_SELECT_CURRENT_INDEXED_DOCUMENT_SOURCE_SQL = """
SELECT
    document_sources.document_type,
    document_sources.document_id,
    document_sources.source_version,
    document_sources.title,
    document_sources.source_created_at,
    document_sources.source_updated_at,
    document_sources.metadata
FROM document_sources
JOIN document_index_records
  ON document_index_records.document_id = document_sources.document_id
 AND document_index_records.deleted_at IS NULL
WHERE document_sources.tenant_id = %s
  AND document_sources.document_id = %s
  AND document_sources.deleted_at IS NULL
LIMIT 1
"""

_SELECT_CURRENT_DOCUMENT_FOLDER_IDS_SQL = """
SELECT folder_id
FROM source_document_folder_relations
WHERE tenant_id = %s
  AND document_id = %s
ORDER BY folder_id
"""

_SELECT_CURRENT_DOCUMENT_SIGNAL_TEXT_SQL = """
SELECT
    signal_id,
    signal_type,
    signal_key,
    text,
    confidence
FROM document_signals
WHERE document_id = %s
ORDER BY
    CASE signal_type
        WHEN 'summary' THEN 0
        WHEN 'concept' THEN 1
        WHEN 'entity' THEN 2
        WHEN 'issue' THEN 3
        WHEN 'commitment' THEN 4
        WHEN 'claim' THEN 5
        ELSE 6
    END,
    confidence DESC NULLS LAST,
    signal_key ASC,
    signal_id ASC
"""

_SELECT_CURRENT_DOCUMENT_DIGEST_SQL = """
SELECT content_digest
FROM document_sources
WHERE tenant_id = %s
  AND document_id = %s
  AND source_version = %s
  AND deleted_at IS NULL
"""


@dataclass(slots=True)
class PostgresIndexedDocumentSourceRepository:
    client: PostgresClient

    def get_current_document_source(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> SourceDocument | None:
        with self.client.connect() as conn:
            row = conn.execute(
                _SELECT_CURRENT_INDEXED_DOCUMENT_SOURCE_SQL,
                (tenant, document_id),
            ).fetchone()
            if row is None:
                return None
            metadata = _metadata_json_object(row_value(row, "metadata", 6))
            source_version = _str(row, "source_version", 2)
            signal_rows = conn.execute(
                _SELECT_CURRENT_DOCUMENT_SIGNAL_TEXT_SQL,
                (document_id,),
            ).fetchall()
        return SourceDocument(
            tenant=tenant,
            document_type=_optional_str(row, "document_type", 0),
            document_id=_str(row, "document_id", 1),
            source_version=source_version,
            title=_str(row, "title", 3),
            body=_signal_body(signal_rows),
            created_at=_timestamp_text(row_value(row, "created_at", 4)),
            updated_at=_timestamp_text(row_value(row, "updated_at", 5)),
            metadata=metadata,
        )

    def get_current_document_folder_ids(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> tuple[str, ...]:
        with self.client.connect() as conn:
            rows = conn.execute(
                _SELECT_CURRENT_DOCUMENT_FOLDER_IDS_SQL,
                (tenant, document_id),
            ).fetchall()
        return tuple(_str(row, "folder_id", 0) for row in rows)

    def current_document_content_digest(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
    ) -> str | None:
        with self.client.connect() as conn:
            return self.current_document_content_digest_with_connection(
                conn,
                tenant=tenant,
                document_id=document_id,
                source_version=source_version,
            )

    def current_document_content_digest_with_connection(
        self,
        conn: Any,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
    ) -> str | None:
        row = conn.execute(
            _SELECT_CURRENT_DOCUMENT_DIGEST_SQL,
            (tenant, document_id, source_version),
        ).fetchone()
        if row is None:
            return None
        return _str(row, "content_digest", 0)


def _signal_body(rows: list[Any]) -> str:
    sorted_rows = sorted(rows, key=_signal_sort_key)
    texts: list[str] = []
    for row in sorted_rows:
        text = _str(row, "text", 3).strip()
        if text:
            texts.append(text)
    return "\n\n".join(texts)


def _signal_sort_key(row: Any) -> tuple[int, float, str, str]:
    confidence = row_value(row, "confidence", 4)
    confidence_score = confidence if isinstance(confidence, int | float) else -1.0
    return (
        _signal_type_order(_str(row, "signal_type", 1)),
        -float(confidence_score),
        _str(row, "signal_key", 2),
        _str(row, "signal_id", 0),
    )


def _signal_type_order(signal_type: str) -> int:
    return {
        "summary": 0,
        "concept": 1,
        "entity": 2,
        "issue": 3,
        "commitment": 4,
        "claim": 5,
    }.get(signal_type, 6)


def _metadata_json_object(value: object) -> JsonObject:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata fields must contain JSON objects.")
    return cast(JsonObject, value)


def _str(row: Any, key: str, index: int) -> str:
    value = row_value(row, key, index)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value


def _optional_str(row: Any, key: str, index: int) -> str | None:
    value = row_value(row, key, index)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string.")
    return value or None


def _timestamp_text(value: object) -> str:
    if value is None:
        return ""
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return str(isoformat())
    return str(value)
