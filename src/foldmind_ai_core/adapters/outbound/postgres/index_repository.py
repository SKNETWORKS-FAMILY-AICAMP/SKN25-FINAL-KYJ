from __future__ import annotations

import hashlib
from typing import Any

from foldmind_ai_core.adapters.outbound.postgres.client import jsonb
from foldmind_ai_core.adapters.outbound.postgres.mappers.document_signal import (
    document_signal_record_from_domain,
    folder_signal_record_from_domain,
)
from foldmind_ai_core.core.application.models.indexing import (
    DeletedDocumentIdentity,
    DeletedFolderIdentity,
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentProfile,
    DocumentSignal,
    FolderSignal,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder

_UPSERT_TENANT_STATE_SQL = """
INSERT INTO tenant_storage_scopes (tenant_id, updated_at)
VALUES (%s, now())
ON CONFLICT (tenant_id)
DO UPDATE SET
    deleted_at = NULL,
    purge_after = NULL,
    updated_at = now()
"""

_UPSERT_DOCUMENT_SOURCE_SQL = """
INSERT INTO document_sources (
    document_id,
    tenant_id,
    document_type,
    source_version,
    source_created_at,
    source_updated_at,
    title,
    content_digest,
    content_size_bytes,
    metadata,
    updated_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (document_id)
DO UPDATE SET
    tenant_id = EXCLUDED.tenant_id,
    document_type = EXCLUDED.document_type,
    source_version = EXCLUDED.source_version,
    source_created_at = EXCLUDED.source_created_at,
    source_updated_at = EXCLUDED.source_updated_at,
    title = EXCLUDED.title,
    content_digest = EXCLUDED.content_digest,
    content_size_bytes = EXCLUDED.content_size_bytes,
    metadata = EXCLUDED.metadata,
    deleted_at = NULL,
    purge_after = NULL,
    updated_at = now()
WHERE document_sources.source_version <= EXCLUDED.source_version
"""

_DOCUMENT_SOURCE_IS_CURRENT_SQL = """
SELECT 1
FROM document_sources
WHERE document_id = %s
  AND tenant_id = %s
  AND source_version = %s
  AND content_digest = %s
  AND deleted_at IS NULL
"""

_DOCUMENT_SOURCE_EXISTS_SQL = """
SELECT 1
FROM document_sources
WHERE tenant_id = %s
  AND document_id = %s
  AND deleted_at IS NULL
LIMIT 1
"""

_UPSERT_DOCUMENT_FOLDER_RELATION_SNAPSHOT_SQL = """
INSERT INTO source_document_folder_relation (
    tenant_id,
    document_id,
    source_version,
    folder_ids,
    updated_at
)
VALUES (%s, %s, %s, %s, now())
ON CONFLICT (tenant_id, document_id)
DO UPDATE SET
    source_version = EXCLUDED.source_version,
    folder_ids = EXCLUDED.folder_ids,
    updated_at = now()
WHERE source_document_folder_relation.source_version <= EXCLUDED.source_version
"""

_DELETE_DOCUMENT_FOLDER_RELATION_SNAPSHOT_SQL = """
DELETE FROM source_document_folder_relation
WHERE document_id = %s
"""

_UPSERT_DOCUMENT_PROFILE_SQL = """
INSERT INTO document_index_records (
    document_id,
    signal_set_version,
    model,
    deleted_at,
    purge_after,
    updated_at
)
VALUES (
    %s, %s, %s, NULL, NULL, now()
)
ON CONFLICT (document_id)
DO UPDATE SET
    signal_set_version = EXCLUDED.signal_set_version,
    model = EXCLUDED.model,
    deleted_at = NULL,
    purge_after = NULL,
    updated_at = now()
"""

_DELETE_DOCUMENT_CHUNKS_SQL = """
DELETE FROM document_chunks
WHERE document_id = %s
"""

_INSERT_DOCUMENT_CHUNK_SQL = """
INSERT INTO document_chunks (
    chunk_id,
    document_id,
    chunk_index,
    text_digest,
    start_offset,
    end_offset
)
VALUES (%s, %s, %s, %s, %s, %s)
"""

_DELETE_DOCUMENT_SIGNALS_SQL = """
DELETE FROM document_signals
WHERE document_id = %s
"""

_INSERT_DOCUMENT_SIGNAL_SQL = """
INSERT INTO document_signals (
    signal_id,
    document_id,
    signal_type,
    signal_key,
    text,
    attributes_json,
    evidence_json,
    confidence,
    extractor_name,
    extractor_version,
    updated_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (signal_id)
DO UPDATE SET
    document_id = EXCLUDED.document_id,
    signal_type = EXCLUDED.signal_type,
    signal_key = EXCLUDED.signal_key,
    text = EXCLUDED.text,
    attributes_json = EXCLUDED.attributes_json,
    evidence_json = EXCLUDED.evidence_json,
    confidence = EXCLUDED.confidence,
    extractor_name = EXCLUDED.extractor_name,
    extractor_version = EXCLUDED.extractor_version,
    updated_at = now()
"""

_SELECT_DOCUMENT_DELETE_IDENTITY_SQL = """
SELECT tenant_id, document_id
FROM document_sources
WHERE document_id = %s
"""

_MARK_DOCUMENT_SOURCE_DELETED_SQL = """
UPDATE document_sources
SET deleted_at = COALESCE(deleted_at, now()),
    purge_after = COALESCE(purge_after, now() + interval '90 days'),
    updated_at = now()
WHERE tenant_id = %s
  AND document_id = %s
"""

_MARK_DOCUMENT_INDEX_RECORD_DELETED_SQL = """
UPDATE document_index_records
SET deleted_at = COALESCE(deleted_at, now()),
    purge_after = COALESCE(purge_after, now() + interval '90 days'),
    updated_at = now()
WHERE document_id = %s
"""

_SELECT_DOCUMENT_DELETE_AFFECTED_FOLDER_IDS_SQL = """
SELECT DISTINCT folder_id
FROM (
    SELECT unnest(folder_ids) AS folder_id
    FROM source_document_folder_relation
    WHERE document_id = %s

    UNION

    SELECT folder_id
    FROM folder_signals
    WHERE related_document_id = %s
) affected_folders
WHERE folder_id IS NOT NULL
ORDER BY folder_id
"""

_DELETE_AFFECTED_FOLDER_SIGNALS_SQL = """
DELETE FROM folder_signals
WHERE folder_id = ANY(%s)
"""

_MARK_AFFECTED_FOLDER_INDEX_RECORDS_DELETED_SQL = """
UPDATE folder_index_records
SET deleted_at = COALESCE(deleted_at, now()),
    purge_after = COALESCE(purge_after, now() + interval '90 days'),
    updated_at = now()
WHERE folder_id = ANY(%s)
"""

_UPSERT_FOLDER_SOURCE_SQL = """
INSERT INTO folder_sources (
    folder_id,
    tenant_id,
    source_version,
    source_created_at,
    source_updated_at,
    name,
    path,
    parent_folder_id,
    description,
    metadata,
    updated_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (folder_id)
DO UPDATE SET
    tenant_id = EXCLUDED.tenant_id,
    source_version = EXCLUDED.source_version,
    source_created_at = EXCLUDED.source_created_at,
    source_updated_at = EXCLUDED.source_updated_at,
    name = EXCLUDED.name,
    path = EXCLUDED.path,
    parent_folder_id = EXCLUDED.parent_folder_id,
    description = EXCLUDED.description,
    metadata = EXCLUDED.metadata,
    deleted_at = NULL,
    purge_after = NULL,
    updated_at = now()
WHERE folder_sources.source_version <= EXCLUDED.source_version
"""

_FOLDER_SOURCE_IS_CURRENT_SQL = """
SELECT 1
FROM folder_sources
WHERE folder_id = %s
  AND tenant_id = %s
  AND source_version = %s
  AND deleted_at IS NULL
"""

_UPSERT_FOLDER_INDEX_SQL = """
INSERT INTO folder_index_records (
    folder_id,
    signal_set_version,
    model,
    deleted_at,
    purge_after,
    updated_at
)
VALUES (%s, %s, %s, NULL, NULL, now())
ON CONFLICT (folder_id)
DO UPDATE SET
    signal_set_version = EXCLUDED.signal_set_version,
    model = EXCLUDED.model,
    deleted_at = NULL,
    purge_after = NULL,
    updated_at = now()
"""

_DELETE_FOLDER_SIGNALS_SQL = """
DELETE FROM folder_signals
WHERE folder_id = %s
"""

_INSERT_FOLDER_SIGNAL_SQL = """
INSERT INTO folder_signals (
    signal_id,
    folder_id,
    signal_type,
    signal_key,
    text,
    related_document_id,
    attributes_json,
    evidence_json,
    confidence,
    extractor_name,
    extractor_version,
    updated_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (signal_id)
DO UPDATE SET
    folder_id = EXCLUDED.folder_id,
    signal_type = EXCLUDED.signal_type,
    signal_key = EXCLUDED.signal_key,
    text = EXCLUDED.text,
    related_document_id = EXCLUDED.related_document_id,
    attributes_json = EXCLUDED.attributes_json,
    evidence_json = EXCLUDED.evidence_json,
    confidence = EXCLUDED.confidence,
    extractor_name = EXCLUDED.extractor_name,
    extractor_version = EXCLUDED.extractor_version,
    updated_at = now()
"""

_SELECT_FOLDER_DELETE_IDENTITY_SQL = """
SELECT tenant_id, folder_id
FROM folder_sources
WHERE folder_id = %s
"""

_MARK_FOLDER_SOURCE_DELETED_SQL = """
UPDATE folder_sources
SET deleted_at = COALESCE(deleted_at, now()),
    purge_after = COALESCE(purge_after, now() + interval '90 days'),
    updated_at = now()
WHERE tenant_id = %s
  AND folder_id = %s
"""

_MARK_FOLDER_INDEX_RECORD_DELETED_SQL = """
UPDATE folder_index_records
SET deleted_at = COALESCE(deleted_at, now()),
    purge_after = COALESCE(purge_after, now() + interval '90 days'),
    updated_at = now()
WHERE folder_id = %s
"""


class PostgresIndexRepository:
    def upsert_document_index_with_connection(
        self,
        conn: Any,
        *,
        document: SourceDocument,
        chunks: tuple[DocumentChunk, ...],
        profile: DocumentProfile,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        tenant = document.tenant
        content_digest = _sha256(document.full_text)
        content_size_bytes = len(document.full_text.encode("utf-8"))

        self._ensure_tenant(conn, tenant)
        conn.execute(
            _UPSERT_DOCUMENT_SOURCE_SQL,
            (
                document.document_id,
                tenant,
                document.document_type,
                document.source_version,
                document.created_at,
                document.updated_at,
                document.title,
                content_digest,
                content_size_bytes,
                jsonb(document.metadata),
            ),
        )
        if not self._document_source_is_current(
            conn,
            document=document,
            content_digest=content_digest,
        ):
            return
        conn.execute(
            _UPSERT_DOCUMENT_PROFILE_SQL,
            (
                document.document_id,
                profile.signal_set_version,
                profile.model,
            ),
        )
        conn.execute(_DELETE_DOCUMENT_CHUNKS_SQL, (document.document_id,))
        for chunk in chunks:
            conn.execute(
                _INSERT_DOCUMENT_CHUNK_SQL,
                (
                    chunk.chunk_id,
                    document.document_id,
                    chunk.chunk_index,
                    chunk.text_hash,
                    chunk.start_offset,
                    chunk.end_offset,
                ),
            )
        conn.execute(_DELETE_DOCUMENT_SIGNALS_SQL, (document.document_id,))
        self._insert_signals_with_connection(
            conn,
            document_id=document.document_id,
            signals=signals,
        )

    def replace_document_folder_relation_snapshot_with_connection(
        self,
        conn: Any,
        *,
        snapshot: SourceDocumentFolderRelationSnapshot,
    ) -> bool:
        if not self._document_source_exists(
            conn,
            tenant=snapshot.tenant,
            document_id=snapshot.document_id,
        ):
            return False
        self._ensure_tenant(conn, snapshot.tenant)
        conn.execute(
            _UPSERT_DOCUMENT_FOLDER_RELATION_SNAPSHOT_SQL,
            (
                snapshot.tenant,
                snapshot.document_id,
                snapshot.source_version,
                list(snapshot.folder_ids),
            ),
        )
        return True

    def mark_document_deleted_with_connection(
        self,
        conn: Any,
        *,
        document_id: str,
    ) -> DeletedDocumentIdentity | None:
        row = conn.execute(_SELECT_DOCUMENT_DELETE_IDENTITY_SQL, (document_id,)).fetchone()
        if row is None:
            return None
        identity = DeletedDocumentIdentity(
            tenant=str(row[0]),
            document_id=str(row[1]),
            affected_folder_ids=self._document_delete_affected_folder_ids(
                conn,
                document_id=str(row[1]),
            ),
        )
        if identity.affected_folder_ids:
            conn.execute(
                _DELETE_AFFECTED_FOLDER_SIGNALS_SQL,
                (list(identity.affected_folder_ids),),
            )
            conn.execute(
                _MARK_AFFECTED_FOLDER_INDEX_RECORDS_DELETED_SQL,
                (list(identity.affected_folder_ids),),
            )
        conn.execute(_DELETE_DOCUMENT_SIGNALS_SQL, (identity.document_id,))
        conn.execute(_DELETE_DOCUMENT_CHUNKS_SQL, (identity.document_id,))
        conn.execute(_DELETE_DOCUMENT_FOLDER_RELATION_SNAPSHOT_SQL, (identity.document_id,))
        conn.execute(_MARK_DOCUMENT_INDEX_RECORD_DELETED_SQL, (identity.document_id,))
        conn.execute(
            _MARK_DOCUMENT_SOURCE_DELETED_SQL,
            (identity.tenant, identity.document_id),
        )
        return identity

    def upsert_folder_index_with_connection(
        self,
        conn: Any,
        *,
        folder: SourceFolder,
        signals: tuple[FolderSignal, ...] = (),
    ) -> None:
        tenant = folder.tenant

        self._ensure_tenant(conn, tenant)
        conn.execute(
            _UPSERT_FOLDER_SOURCE_SQL,
            (
                folder.folder_id,
                tenant,
                folder.source_version,
                folder.created_at,
                folder.updated_at,
                folder.name,
                folder.path,
                folder.parent_folder_id,
                folder.description,
                jsonb(folder.metadata),
            ),
        )
        if not self._folder_source_is_current(
            conn,
            folder=folder,
        ):
            return
        conn.execute(
            _UPSERT_FOLDER_INDEX_SQL,
            (
                folder.folder_id,
                _signal_set_version(signals),
                _signal_model(signals),
            ),
        )
        conn.execute(_DELETE_FOLDER_SIGNALS_SQL, (folder.folder_id,))
        self._insert_folder_signals_with_connection(
            conn,
            folder_id=folder.folder_id,
            signals=signals,
        )

    def mark_folder_deleted_with_connection(
        self,
        conn: Any,
        *,
        folder_id: str,
    ) -> DeletedFolderIdentity | None:
        row = conn.execute(_SELECT_FOLDER_DELETE_IDENTITY_SQL, (folder_id,)).fetchone()
        if row is None:
            return None
        identity = DeletedFolderIdentity(tenant=str(row[0]), folder_id=str(row[1]))
        conn.execute(_DELETE_FOLDER_SIGNALS_SQL, (identity.folder_id,))
        conn.execute(_MARK_FOLDER_INDEX_RECORD_DELETED_SQL, (identity.folder_id,))
        conn.execute(_MARK_FOLDER_SOURCE_DELETED_SQL, (identity.tenant, identity.folder_id))
        return identity

    def _ensure_tenant(self, conn: Any, tenant: str) -> None:
        conn.execute(_UPSERT_TENANT_STATE_SQL, (tenant,))

    def _document_source_is_current(
        self,
        conn: Any,
        *,
        document: SourceDocument,
        content_digest: str,
    ) -> bool:
        row = conn.execute(
            _DOCUMENT_SOURCE_IS_CURRENT_SQL,
            (
                document.document_id,
                document.tenant,
                document.source_version,
                content_digest,
            ),
        ).fetchone()
        return row is not None

    def _document_source_exists(
        self,
        conn: Any,
        *,
        tenant: str,
        document_id: str,
    ) -> bool:
        row = conn.execute(
            _DOCUMENT_SOURCE_EXISTS_SQL,
            (tenant, document_id),
        ).fetchone()
        return row is not None

    def _document_delete_affected_folder_ids(
        self,
        conn: Any,
        *,
        document_id: str,
    ) -> tuple[str, ...]:
        rows = conn.execute(
            _SELECT_DOCUMENT_DELETE_AFFECTED_FOLDER_IDS_SQL,
            (document_id, document_id),
        ).fetchall()
        return _text_tuple_from_rows(rows)

    def _folder_source_is_current(
        self,
        conn: Any,
        *,
        folder: SourceFolder,
    ) -> bool:
        row = conn.execute(
            _FOLDER_SOURCE_IS_CURRENT_SQL,
            (
                folder.folder_id,
                folder.tenant,
                folder.source_version,
            ),
        ).fetchone()
        return row is not None

    def _insert_signals_with_connection(
        self,
        conn: Any,
        *,
        document_id: str,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        for signal in signals:
            record = document_signal_record_from_domain(signal)
            conn.execute(
                _INSERT_DOCUMENT_SIGNAL_SQL,
                (
                    record.signal_id,
                    document_id,
                    record.signal_type,
                    record.signal_key,
                    record.text,
                    jsonb(record.attributes),
                    jsonb(list(record.evidence)),
                    record.confidence,
                    record.extractor_name,
                    record.extractor_version,
                ),
            )

    def _insert_folder_signals_with_connection(
        self,
        conn: Any,
        *,
        folder_id: str,
        signals: tuple[FolderSignal, ...],
    ) -> None:
        for signal in signals:
            record = folder_signal_record_from_domain(signal)
            conn.execute(
                _INSERT_FOLDER_SIGNAL_SQL,
                (
                    record.signal_id,
                    folder_id,
                    record.signal_type,
                    record.signal_key,
                    record.text,
                    record.related_document_id,
                    jsonb(record.attributes),
                    jsonb(list(record.evidence)),
                    record.confidence,
                    record.extractor_name,
                    record.extractor_version,
                ),
            )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _text_tuple_from_rows(rows: list[tuple[Any, ...]]) -> tuple[str, ...]:
    values: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if not row or row[0] is None:
            continue
        value = str(row[0]).strip()
        if not value or value in seen:
            continue
        values.append(value)
        seen.add(value)
    return tuple(values)


def _signal_set_version(signals: tuple[FolderSignal, ...]) -> str:
    for signal in signals:
        value = signal.metadata.get("signal_set_version")
        if isinstance(value, str) and value.strip():
            return value
    return "1"


def _signal_model(signals: tuple[FolderSignal, ...]) -> str:
    for signal in signals:
        value = signal.metadata.get("model")
        if isinstance(value, str):
            return value
    return ""
