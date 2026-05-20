from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
from foldmind_ai_core.core.application.ports.outbound.vector_store import (
    VectorWriteResult,
)
from foldmind_ai_core.core.application.projections.vector import (
    DocumentChunkVectorProjection,
    DocumentSignalVectorProjection,
    DocumentVectorProjection,
    FolderSignalVectorProjection,
    FolderVectorProjection,
)

_UPSERT_VECTOR_PROJECTION_SQL = """
INSERT INTO vector_projection_records (
    tenant_id,
    collection_name,
    point_id,
    source_kind,
    source_id,
    vector_item_kind,
    vector_item_id,
    updated_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, now())
ON CONFLICT (collection_name, point_id)
DO UPDATE SET
    tenant_id = EXCLUDED.tenant_id,
    source_kind = EXCLUDED.source_kind,
    source_id = EXCLUDED.source_id,
    vector_item_kind = EXCLUDED.vector_item_kind,
    vector_item_id = EXCLUDED.vector_item_id,
    updated_at = now()
"""

_DELETE_VECTOR_PROJECTIONS_SQL = """
DELETE FROM vector_projection_records
WHERE source_kind = %s
  AND source_id = %s
  AND vector_item_kind = ANY(%s)
"""


@dataclass(slots=True)
class PostgresProjectionLedgerRepository:
    client: PostgresClient

    def record_document_vector_projected(
        self,
        *,
        projection: DocumentVectorProjection,
        write: VectorWriteResult,
    ) -> None:
        with self.client.transaction() as conn:
            self._upsert_vector_projection(
                conn,
                tenant=projection.tenant,
                source_kind="document",
                source_id=projection.document_id,
                vector_item_kind="document",
                vector_item_id=projection.document_id,
                write=write,
            )

    def record_chunk_vectors_projected(
        self,
        *,
        projections: tuple[DocumentChunkVectorProjection, ...],
        writes: tuple[VectorWriteResult, ...],
    ) -> None:
        if not projections:
            return
        with self.client.transaction() as conn:
            for projection, write in zip(projections, writes, strict=True):
                self._upsert_vector_projection(
                    conn,
                    tenant=projection.tenant,
                    source_kind="document",
                    source_id=projection.document_id,
                    vector_item_kind="chunk",
                    vector_item_id=projection.chunk_id,
                    write=write,
                )

    def record_signal_vectors_projected(
        self,
        *,
        projections: tuple[DocumentSignalVectorProjection, ...],
        writes: tuple[VectorWriteResult, ...],
    ) -> None:
        if not projections:
            return
        with self.client.transaction() as conn:
            for projection, write in zip(projections, writes, strict=True):
                self._upsert_vector_projection(
                    conn,
                    tenant=projection.tenant,
                    source_kind="document",
                    source_id=projection.document_id,
                    vector_item_kind="signal",
                    vector_item_id=projection.signal_id,
                    write=write,
                )

    def record_folder_signal_vectors_projected(
        self,
        *,
        projections: tuple[FolderSignalVectorProjection, ...],
        writes: tuple[VectorWriteResult, ...],
    ) -> None:
        if not projections:
            return
        with self.client.transaction() as conn:
            for projection, write in zip(projections, writes, strict=True):
                self._upsert_vector_projection(
                    conn,
                    tenant=projection.tenant,
                    source_kind="folder",
                    source_id=projection.folder_id,
                    vector_item_kind="signal",
                    vector_item_id=projection.signal_id,
                    write=write,
                )

    def record_folder_vector_projected(
        self,
        *,
        projection: FolderVectorProjection,
        write: VectorWriteResult,
    ) -> None:
        with self.client.transaction() as conn:
            self._upsert_vector_projection(
                conn,
                tenant=projection.tenant,
                source_kind="folder",
                source_id=projection.folder_id,
                vector_item_kind="folder",
                vector_item_id=projection.folder_id,
                write=write,
            )

    def delete_document_vector_records(
        self,
        *,
        document_id: str,
    ) -> None:
        with self.client.transaction() as conn:
            conn.execute(
                _DELETE_VECTOR_PROJECTIONS_SQL,
                ("document", document_id, ["document"]),
            )

    def delete_chunk_vector_records(
        self,
        *,
        document_id: str,
    ) -> None:
        with self.client.transaction() as conn:
            conn.execute(
                _DELETE_VECTOR_PROJECTIONS_SQL,
                ("document", document_id, ["chunk"]),
            )

    def delete_signal_vector_records(
        self,
        *,
        document_id: str,
    ) -> None:
        with self.client.transaction() as conn:
            conn.execute(
                _DELETE_VECTOR_PROJECTIONS_SQL,
                ("document", document_id, ["signal"]),
            )

    def delete_folder_signal_vector_records(self, *, folder_id: str) -> None:
        with self.client.transaction() as conn:
            conn.execute(
                _DELETE_VECTOR_PROJECTIONS_SQL,
                ("folder", folder_id, ["signal"]),
            )

    def delete_folder_vector_records(self, *, folder_id: str) -> None:
        with self.client.transaction() as conn:
            conn.execute(
                _DELETE_VECTOR_PROJECTIONS_SQL,
                ("folder", folder_id, ["folder"]),
            )

    def _upsert_vector_projection(
        self,
        conn: Any,
        *,
        tenant: str,
        source_kind: str,
        source_id: str,
        vector_item_kind: str,
        vector_item_id: str,
        write: VectorWriteResult,
    ) -> None:
        conn.execute(
            _UPSERT_VECTOR_PROJECTION_SQL,
            (
                tenant,
                write.collection_name,
                write.point_id,
                source_kind,
                source_id,
                vector_item_kind,
                vector_item_id,
            ),
        )
