from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient

_CURRENT_DOCUMENT_SOURCE_SQL = """
SELECT 1
FROM document_sources
WHERE tenant_id = %s
  AND document_id = %s
  AND source_version = %s
  AND content_digest = %s
  AND deleted_at IS NULL
LIMIT 1
"""

_CURRENT_FOLDER_SOURCE_SQL = """
SELECT 1
FROM folder_sources
WHERE tenant_id = %s
  AND folder_id = %s
  AND source_version = %s
  AND deleted_at IS NULL
LIMIT 1
"""

_CURRENT_DOCUMENT_FOLDER_RELATION_SNAPSHOT_SQL = """
SELECT 1
FROM document_sources
WHERE tenant_id = %s
  AND document_id = %s
  AND source_version = %s
  AND deleted_at IS NULL
LIMIT 1
"""

_CURRENT_FOLDER_INDEX_INPUT_DIGEST_SQL = """
SELECT 1
FROM folder_index_records fir
JOIN folder_sources fs ON fs.folder_id = fir.folder_id
WHERE fs.tenant_id = %s
  AND fir.folder_id = %s
  AND fir.index_input_digest = %s
  AND fir.deleted_at IS NULL
LIMIT 1
"""


@dataclass(slots=True)
class PostgresSourceFreshnessRepository:
    client: PostgresClient

    def is_current_document_source(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
        content_digest: str,
    ) -> bool:
        with self.client.connect() as conn:
            return (
                conn.execute(
                    _CURRENT_DOCUMENT_SOURCE_SQL,
                    (tenant, document_id, source_version, content_digest),
                ).fetchone()
                is not None
            )

    def is_current_folder_source(
        self,
        *,
        tenant: str,
        folder_id: str,
        source_version: str,
    ) -> bool:
        with self.client.connect() as conn:
            return (
                conn.execute(
                    _CURRENT_FOLDER_SOURCE_SQL,
                    (tenant, folder_id, source_version),
                ).fetchone()
                is not None
            )

    def is_current_document_folder_relation_snapshot(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
    ) -> bool:
        with self.client.connect() as conn:
            return (
                conn.execute(
                    _CURRENT_DOCUMENT_FOLDER_RELATION_SNAPSHOT_SQL,
                    (tenant, document_id, source_version),
                ).fetchone()
                is not None
            )

    def is_current_folder_index_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
        index_input_digest: str,
    ) -> bool:
        with self.client.connect() as conn:
            return (
                conn.execute(
                    _CURRENT_FOLDER_INDEX_INPUT_DIGEST_SQL,
                    (tenant, folder_id, index_input_digest),
                ).fetchone()
                is not None
            )
