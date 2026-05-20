from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from foldmind_ai_core.adapters.outbound.postgres.client import (
    PostgresClient,
    jsonb,
    row_value,
)
from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult


_SEARCH_DOCUMENT_CHUNKS_SQL = """
SELECT
    dc.tenant_id,
    ds.document_type,
    dc.document_id,
    ds.source_version,
    dc.index_input_digest,
    ds.source_created_at,
    ds.source_updated_at,
    dc.chunk_id::text,
    dc.chunk_index,
    dc.search_text,
    dc.source_start_offset,
    dc.source_end_offset,
    ds.metadata,
    ts_rank_cd(dc.search_vector, plainto_tsquery('simple', %s)) AS score
FROM document_chunks dc
JOIN document_sources ds
  ON ds.tenant_id = dc.tenant_id
 AND ds.document_id = dc.document_id
WHERE dc.tenant_id = %s
  AND ds.deleted_at IS NULL
  AND dc.search_vector @@ plainto_tsquery('simple', %s)
{scope_filters}
ORDER BY score DESC, ds.source_updated_at DESC, dc.chunk_index ASC
LIMIT %s
"""


@dataclass(slots=True)
class PostgresDocumentKeywordSearchStore:
    client: PostgresClient

    def __init__(
        self,
        *,
        client: PostgresClient | None = None,
        settings: PostgresSettings | None = None,
    ) -> None:
        if client is None:
            if settings is None:
                raise ValueError("Either client or settings must be provided.")
            client = PostgresClient(settings=settings)
        self.client = client

    def search_chunks(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        query = query_text.strip()
        if not query or top_k <= 0:
            return []
        scope_sql, scope_params = _scope_filters(scope)
        sql = _SEARCH_DOCUMENT_CHUNKS_SQL.format(scope_filters=scope_sql)
        params = (query, tenant, query, *scope_params, top_k)
        with self.client.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_retrieval_result_from_row(row) for row in rows]


def _scope_filters(scope: SearchScope | None) -> tuple[str, tuple[Any, ...]]:
    if scope is None:
        return "", ()

    clauses: list[str] = []
    params: list[Any] = []
    if scope.document_type is not None:
        clauses.append("  AND ds.document_type = %s")
        params.append(scope.document_type)
    if scope.document_id is not None:
        clauses.append("  AND dc.document_id = %s")
        params.append(scope.document_id)
    if scope.document_ids:
        clauses.append("  AND dc.document_id = ANY(%s)")
        params.append(list(scope.document_ids))
    if scope.folder_ids:
        clauses.append(
            """
  AND EXISTS (
      SELECT 1
      FROM source_document_folder_relations sdfr
      WHERE sdfr.tenant_id = dc.tenant_id
        AND sdfr.document_id = dc.document_id
        AND sdfr.folder_id = ANY(%s)
  )
""".rstrip()
        )
        params.append(list(scope.folder_ids))
    if scope.created_at is not None:
        _timestamp_filters(
            clauses=clauses,
            params=params,
            column="ds.source_created_at",
            value=scope.created_at,
        )
    if scope.updated_at is not None:
        _timestamp_filters(
            clauses=clauses,
            params=params,
            column="ds.source_updated_at",
            value=scope.updated_at,
        )
    if scope.metadata_filter:
        clauses.append("  AND ds.metadata @> %s")
        params.append(jsonb(scope.metadata_filter))
    return ("\n" + "\n".join(clauses) if clauses else ""), tuple(params)


def _timestamp_filters(
    *,
    clauses: list[str],
    params: list[Any],
    column: str,
    value: Any,
) -> None:
    for operator, timestamp in (
        (">", value.gt),
        (">=", value.gte),
        ("<", value.lt),
        ("<=", value.lte),
    ):
        if timestamp is None:
            continue
        clauses.append(f"  AND {column} {operator} %s")
        params.append(timestamp)


def _retrieval_result_from_row(row: Any) -> RetrievalResult:
    search_text = str(row_value(row, "search_text", 9))
    chunk = DocumentChunk(
        tenant=str(row_value(row, "tenant_id", 0)),
        document_type=_optional_text(row_value(row, "document_type", 1)),
        document_id=str(row_value(row, "document_id", 2)),
        source_version=str(row_value(row, "source_version", 3)),
        index_input_digest=str(row_value(row, "index_input_digest", 4)),
        created_at=str(row_value(row, "source_created_at", 5)),
        updated_at=str(row_value(row, "source_updated_at", 6)),
        chunk_id=str(row_value(row, "chunk_id", 7)),
        chunk_index=int(row_value(row, "chunk_index", 8)),
        chunking_version="",
        text=search_text,
        text_hash=hashlib.sha256(search_text.encode("utf-8")).hexdigest(),
        start_offset=int(row_value(row, "source_start_offset", 10)),
        end_offset=int(row_value(row, "source_end_offset", 11)),
        embedding_model="",
        embedding_version="",
        index_schema_version="",
        metadata=dict(row_value(row, "metadata", 12) or {}),
    )
    return RetrievalResult(chunk=chunk, score=float(row_value(row, "score", 13)))


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
