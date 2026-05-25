from __future__ import annotations

import unittest
from collections.abc import Iterable
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import datetime
from typing import Any

from sqlalchemy import insert
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Executable

from foldmind_ai_core.adapters.outbound.postgres.indexing_write_session import (
    PostgresIndexingWriteSessionProvider,
)
from foldmind_ai_core.adapters.outbound.postgres.mappers.task import (
    host_action_rows_from_snapshot,
    task_event_rows_from_snapshot,
    task_input_rows_from_snapshot,
    task_job_result_rows_from_snapshot,
    task_job_rows_from_snapshot,
    task_row_from_snapshot,
)
from foldmind_ai_core.adapters.outbound.postgres.models.document_projections import (
    DocumentChunkRow,
    DocumentSignalRow,
)
from foldmind_ai_core.adapters.outbound.postgres.models.sources import (
    DocumentSourceRow,
    FolderSourceRow,
)
from foldmind_ai_core.adapters.outbound.postgres.models.task import TaskRow
from foldmind_ai_core.adapters.outbound.postgres.policies.retention_policy import (
    PurgeAfterPolicy,
)
from foldmind_ai_core.adapters.outbound.postgres.projection_ledger_session import (
    PostgresProjectionLedgerSessionProvider,
)
from foldmind_ai_core.adapters.outbound.postgres.source_freshness_checker import (
    PostgresSourceFreshnessChecker,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    document_relation_repository as document_relations,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    document_projection_repository as document_projections,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    document_source_repository as document_sources,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    folder_projection_repository as folder_projections,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    folder_source_repository as folder_sources,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    outbox_repository as outbox,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    projection_ledger_repository as projection_ledgers,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    task_repository as tasks,
)
from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
from foldmind_ai_core.adapters.outbound.postgres.store.document_folder_relation_store import (
    DocumentFolderRelationStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_index_record_store import (
    DocumentIndexRecordStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_chunk_store import (
    DocumentChunkStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_source_store import (
    DocumentSourceStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_signal_store import (
    DocumentSignalStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.folder_index_record_store import (
    FolderIndexRecordStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.folder_signal_store import (
    FolderSignalStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.folder_source_store import (
    FolderSourceStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.outbox_store import (
    OutboxEventStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.host_action_store import (
    HostActionStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.projection_ledger_store import (
    VectorProjectionRecordStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_event_store import (
    TaskEventStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_input_store import (
    TaskInputStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_job_result_store import (
    TaskJobResultStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_job_store import (
    TaskJobStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_store import TaskStore
from foldmind_ai_core.adapters.outbound.postgres.store.tenant_storage_scope_store import (
    TenantStorageScopeStore,
)
from foldmind_ai_core.adapters.outbound.postgres.task_session import (
    PostgresTaskSessionProvider,
)
from foldmind_ai_core.core.application.mappers.outbox_events import document_deleted_event
from foldmind_ai_core.core.application.models.search import SearchScope
from foldmind_ai_core.core.application.services.indexing.folder_signal_invalidation_service import (
    FolderSignalInvalidationService,
)
from foldmind_ai_core.core.application.models.generation import (
    DocumentRecommendation,
    DocumentSearchResult,
    GeneratedTextResult,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.document_index_state import DocumentIndexState
from foldmind_ai_core.core.domain.models.vector_projection_state import (
    VectorProjectionState,
)
from foldmind_ai_core.core.domain.models.folder_index_state import (
    FolderIndexState,
)
from foldmind_ai_core.core.domain.models.document_signals import (
    DocumentSignal,
    DocumentSignalEvidence,
    DocumentSignalType,
)
from foldmind_ai_core.core.domain.models.folder_signals import (
    FolderSignal,
    FolderSignalType,
)
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.models.document_folder_relations import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.application.models.retrieval import RetrievedDocument
from foldmind_ai_core.core.domain.models.host_actions import (
    CreateFolderInput,
    HostAction,
    HostActionPolicy,
    HostActionStatus,
    HostActionType,
)
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskEvent,
    TaskEventType,
    TaskFinalResult,
    TaskInputEntry,
    TaskJob,
    TaskJobResult,
    TaskJobStatus,
    TaskOutputType,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.core.domain.services.document_signal_service import DocumentSignalService
from foldmind_ai_core.core.domain.services.folder_projection_digest_service import (
    FolderProjectionDigestService,
)
from foldmind_ai_core.core.domain.services.folder_signal_service import FolderSignalService

TASK_ID = "55555555-5555-4555-8555-555555555555"
ACTION_ID = "66666666-6666-4666-8666-666666666666"
JOB_ID = "77777777-7777-4777-8777-777777777777"
OUTPUT_ID = "88888888-8888-4888-8888-888888888888"
SEARCH_OUTPUT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
EVENT_ID = "99999999-9999-4999-8999-999999999999"


class FakeCursor:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows

    def fetchone(self) -> tuple[Any, ...] | None:
        return self.rows[0] if self.rows else None

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows

    def all(self) -> list[tuple[Any, ...]]:
        return self.rows

    def scalar_one_or_none(self) -> Any | None:
        row = self.fetchone()
        return None if row is None else row[0]

    def scalars(self) -> FakeScalarCursor:
        return FakeScalarCursor(self.rows)


class FakeScalarCursor:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return [row[0] for row in self.rows]


class FakeConnection(AsyncSession):
    def __init__(
        self,
        rows: list[tuple[Any, ...]] | None = None,
        row_sets: list[list[tuple[Any, ...]]] | None = None,
    ) -> None:
        self.rows = rows or []
        self.row_sets = row_sets or []
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def begin(self) -> object:
        class Transaction:
            async def __aenter__(self) -> None:
                return None

            async def __aexit__(
                self,
                exc_type: object,
                exc: object,
                traceback: object,
            ) -> bool:
                return False

        return Transaction()

    async def connection(self) -> FakeConnection:
        return self

    async def exec_driver_sql(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> FakeCursor:
        return self._execute_sql(_driver_sql_to_percent(sql), params)

    async def execute(
        self,
        statement: Executable | str,
        params: Any = None,
        *args: Any,
        **kwargs: Any,
    ) -> FakeCursor:
        sql, bound_params = _compiled_sql(statement, params)
        return self._execute_sql(sql, bound_params)

    def add_all(self, instances: Iterable[Any]) -> None:
        for instance in instances:
            self.add(instance)

    def add(self, instance: Any) -> None:
        sql, params = _compiled_sql(
            insert(type(instance)).values(_orm_insert_values(instance))
        )
        self._execute_sql(sql, params)

    async def flush(self, objects: Any = None) -> None:
        return None

    def _execute_sql(self, sql: str, params: tuple[Any, ...] = ()) -> FakeCursor:
        self.calls.append((sql, params))
        upper_sql = sql.lstrip().upper()
        returns_rows = (
            upper_sql.startswith("SELECT")
            or upper_sql.startswith("WITH")
            or "RETURNING" in upper_sql
        )
        if (
            upper_sql.startswith("SELECT 1")
            and ("FROM DOCUMENT_SOURCES" in upper_sql or "FROM FOLDER_SOURCES" in upper_sql)
            and not self.row_sets
        ):
            return FakeCursor([(1,)])
        rows = self.row_sets.pop(0) if returns_rows and self.row_sets else self.rows
        return FakeCursor(rows)


class TransactionalFakeConnection(FakeConnection):
    def __init__(
        self,
        *,
        fail_on_outbox: bool = False,
        fail_on_sql: str | None = None,
    ) -> None:
        super().__init__()
        self.fail_on_outbox = fail_on_outbox
        self.fail_on_sql = fail_on_sql
        self.pending_calls: list[tuple[str, tuple[Any, ...]]] = []
        self.committed_calls: list[tuple[str, tuple[Any, ...]]] = []
        self.rollback_count = 0

    def begin(self) -> object:
        connection = self

        class Transaction:
            async def __aenter__(self) -> None:
                connection.pending_calls = []

            async def __aexit__(
                self,
                exc_type: object,
                exc: object,
                traceback: object,
            ) -> bool:
                if exc_type is None:
                    connection.committed_calls.extend(connection.pending_calls)
                else:
                    connection.rollback_count += 1
                connection.pending_calls = []
                return False

        return Transaction()

    def _execute_sql(self, sql: str, params: tuple[Any, ...] = ()) -> FakeCursor:
        self.calls.append((sql, params))
        self.pending_calls.append((sql, params))
        if self.fail_on_outbox and "INSERT INTO outbox_events" in sql:
            raise RuntimeError("outbox insert failed")
        if self.fail_on_sql is not None and self.fail_on_sql in sql:
            raise RuntimeError("host action insert failed")
        upper_sql = sql.lstrip().upper()
        if upper_sql.startswith("SELECT 1") and (
            "FROM DOCUMENT_SOURCES" in upper_sql or "FROM FOLDER_SOURCES" in upper_sql
        ):
            return FakeCursor([(1,)])
        return FakeCursor([])


class AsyncFakeConnection(FakeConnection):
    """Fake connection used by async session-provider tests."""


class AsyncTransactionalFakeConnection(TransactionalFakeConnection):
    """Transactional fake connection used by async session-provider tests."""


class FakePostgresSessions:
    def __init__(self, connection: AsyncSession) -> None:
        self.connection = connection

    @asynccontextmanager
    async def session(self):
        yield self.connection

    @asynccontextmanager
    async def transaction(self):
        async with self.connection.begin():
            yield self.connection


class PostgresAdapterTests(unittest.IsolatedAsyncioTestCase):
    def test_postgres_settings_reject_blank_dsn(self) -> None:
        with self.assertRaisesRegex(ValueError, "dsn"):
            PostgresSettings(dsn=" ")

        settings = PostgresSettings(dsn=" postgresql://not-used ")
        self.assertEqual(settings.dsn, "postgresql://not-used")

    async def test_document_projection_repository_queries_sparse_keyword_projection(
        self,
    ) -> None:
        chunk_row = _document_chunk_row(
            tenant="tenant-1",
            document_id="doc-1",
            document_index_input_digest="index-input-v1",
            chunk_id="11111111-1111-4111-8111-111111111111",
            chunk_index=0,
            search_text="A useful document.",
            source_start_offset=0,
            source_end_offset=18,
        )
        connection = FakeConnection(
            row_sets=[
                [(chunk_row, 0.5)],
                [(_document_source_row(),)],
            ]
        )

        results = await _document_projection_repository(connection).search_chunks_by_keyword(
            tenant="tenant-1",
            query_text="useful document",
            top_k=5,
            document_id=None,
            document_ids=("doc-1",),
        )

        sql = _all_sql(connection)
        self.assertIn("document_chunks.search_vector @@", sql)
        chunk, score = results[0]
        self.assertEqual(chunk.text, "A useful document.")
        self.assertEqual(chunk.start_offset, 0)
        self.assertEqual(chunk.end_offset, 18)
        self.assertEqual(score, 0.5)

    async def test_indexing_write_session_writes_normalized_document_index(self) -> None:
        connection = FakeConnection()

        async with _postgres_indexing_write_sessions(connection).transaction() as tx:
            await _write_sample_document_index(tx)

        self.assertIn("title", _all_sql(connection))
        self.assertIn("document_index_input_digest", _all_sql(connection))
        self.assertIn("document_signal_input_digest", _all_sql(connection))
        self.assertIn("generation_model", _all_sql(connection))
        self.assertIn("signal_generation_version", _all_sql(connection))
        self.assertIn("document_sources", _all_sql(connection))
        self.assertIn("ON CONFLICT (document_id)", _all_sql(connection))
        self.assertIn("source_created_at", _all_sql(connection))
        self.assertIn("source_updated_at", _all_sql(connection))
        self.assertIn("title = excluded.title", _all_sql(connection).lower())
        self.assertNotIn("substring(document_sources.source_version", _all_sql(connection))
        self.assertNotIn("substring(excluded.source_version", _all_sql(connection))
        self.assertIn(
            "where document_sources.source_version = excluded.source_version "
            "or document_sources.source_updated_at < excluded.source_updated_at",
            _all_sql(connection).lower(),
        )
        self.assertIn("source_document_folder_relation", _all_sql(connection))
        self.assertNotIn("folder_ids = EXCLUDED.folder_ids", _all_sql(connection))
        self.assertNotIn("tag_ids", _all_sql(connection))
        self.assertIn("document_type = excluded.document_type", _all_sql(connection).lower())
        self.assertNotIn("indexed_content_digest", _all_sql(connection))
        self.assertNotIn("title_digest", _all_sql(connection))
        self.assertNotIn("name_digest", _all_sql(connection))
        self.assertNotIn("path_digest", _all_sql(connection))
        self.assertNotIn("parent_folder_id_digest", _all_sql(connection))
        self.assertIn("ON CONFLICT (document_id)", _all_sql(connection))
        self.assertNotIn("ON CONFLICT (signal_id)", _all_sql(connection))
        self.assertNotIn("ON CONFLICT (tenant_id, signal_id)", _all_sql(connection))
        self.assertNotIn("latest_source_version", _all_sql(connection))
        self.assertNotIn("last_seen_at", _all_sql(connection))
        self.assertNotIn(
            "document_index_records (\n    document_index_id,\n    tenant_id", _all_sql(connection)
        )
        self.assertNotIn("source_document_snapshots", _all_sql(connection))
        self.assertNotIn("'metadata_only'", _all_sql(connection))
        self.assertNotIn("purged_at", _all_sql(connection))
        self.assertNotIn("error_code", _all_sql(connection))
        self.assertNotIn("error_message", _all_sql(connection))
        self.assertIn("document_index_records", _all_sql(connection))
        self.assertNotIn("document_profiles", _all_sql(connection))
        self.assertNotIn("summary", _all_sql(connection))
        self.assertNotIn("concepts_json", _all_sql(connection))
        self.assertNotIn("topics", _all_sql(connection))
        self.assertNotIn("suggested_tags", _all_sql(connection))
        self.assertNotIn("document_profile_terms", _all_sql(connection))
        self.assertNotIn("document_profile_folder_suggestions", _all_sql(connection))
        self.assertNotIn("document_profile_items", _all_sql(connection))
        self.assertNotIn("document_profile_evidence_spans", _all_sql(connection))
        self.assertNotIn("document_profile_chunk_mentions", _all_sql(connection))
        self.assertNotIn("folder_documents_ref", _all_sql(connection))
        self.assertNotIn("profile_json", _all_sql(connection))
        self.assertIn("search_text", _all_sql(connection))
        self.assertIn("source_start_offset", _all_sql(connection))
        self.assertIn("source_end_offset", _all_sql(connection))
        self.assertNotIn("text_digest", _all_sql(connection))
        chunk_insert_params = [
            params for sql, params in connection.calls if "INSERT INTO document_chunks" in sql
        ]
        self.assertEqual(len(chunk_insert_params), 1)
        self.assertEqual(
            chunk_insert_params[0][:8],
            (
                "11111111-1111-4111-8111-111111111111",
                "tenant-1",
                "doc-1",
                "index-input-v1",
                0,
                "A useful document.",
                0,
                18,
            ),
        )

    async def test_indexing_write_session_replaces_document_folder_relation(
        self,
    ) -> None:
        connection = FakeConnection()

        async with _postgres_indexing_write_sessions(connection).transaction() as tx:
            await tx.document_relations.replace_folder_relations_for_document(
                snapshot=SourceDocumentFolderRelationSnapshot(
                    tenant="tenant-1",
                    document_id="doc-1",
                    source_version="v1",
                    folder_ids=("folder-1", "folder-2", "folder-1"),
                ),
            )

        sql = _all_sql(connection)
        self.assertNotIn("FROM document_sources", sql)
        self.assertNotIn("source_document_folder_relation_state", sql)
        self.assertIn("DELETE FROM source_document_folder_relations", sql)
        self.assertIn("INSERT INTO source_document_folder_relations", sql)
        self.assertNotIn("folder_ids = EXCLUDED.folder_ids", sql)
        relation_insert_params = [
            params
            for sql, params in connection.calls
            if "INSERT INTO source_document_folder_relations" in sql
        ]
        self.assertEqual(
            [params[:3] for params in relation_insert_params],
            [
                ("tenant-1", "doc-1", "folder-1"),
                ("tenant-1", "doc-1", "folder-2"),
            ],
        )

    async def test_indexing_write_session_represents_empty_folder_membership_as_no_rows(
        self,
    ) -> None:
        connection = FakeConnection()

        async with _postgres_indexing_write_sessions(connection).transaction() as tx:
            await tx.document_relations.replace_folder_relations_for_document(
                snapshot=SourceDocumentFolderRelationSnapshot(
                    tenant="tenant-1",
                    document_id="doc-1",
                    source_version="v2",
                    folder_ids=(),
                ),
            )

        sql = _all_sql(connection)
        self.assertNotIn("FROM document_sources", sql)
        self.assertNotIn("source_document_folder_relation_state", sql)
        self.assertIn("DELETE FROM source_document_folder_relations", sql)
        self.assertNotIn("INSERT INTO source_document_folder_relations", sql)

    async def test_document_source_repository_reads_current_identity_for_update(
        self,
    ) -> None:
        connection = FakeConnection(row_sets=[[("v2",)]])

        async with _postgres_indexing_write_sessions(connection).transaction() as tx:
            identity = await tx.document_sources.current_document_source_identity_for_update(
                tenant="tenant-1",
                document_id="doc-1",
            )

        sql = _all_sql(connection)
        self.assertIsNotNone(identity)
        assert identity is not None
        self.assertEqual(identity.source_version, "v2")
        self.assertIn("FROM document_sources", sql)
        self.assertNotIn("source_document_folder_relation_state", sql)
        self.assertNotIn("DELETE FROM source_document_folder_relations", sql)
        self.assertNotIn("INSERT INTO source_document_folder_relations", sql)

    async def test_indexing_write_session_deletes_documents_by_stored_tenant(
        self,
    ) -> None:
        connection = FakeConnection(
            row_sets=[
                [
                    (
                        _document_source_row(
                            tenant="tenant-1",
                            document_id="doc-1",
                            source_version="source-v1",
                        ),
                    )
                ],
                [("folder-1",), ("folder-2",)],
                [],
                [("folder-1",), ("folder-2",)],
                [
                    (
                        _folder_source_row(
                            folder_id="folder-1",
                            name="Folder 1",
                        ),
                    )
                ],
                [("1",)],
                [("folder-1",)],
                [],
                [("folder-1",)],
                [
                    (
                        _folder_source_row(
                            folder_id="folder-2",
                            name="Folder 2",
                        ),
                    )
                ],
                [("1",)],
                [("folder-2",)],
                [],
                [("folder-2",)],
            ],
        )

        async with _postgres_indexing_write_sessions(
            connection,
            purge_after_days=14,
        ).transaction() as tx:
            identity = await tx.document_sources.document_identity_for_delete("doc-1")
            self.assertIsNotNone(identity)
            direct_folder_ids = await tx.document_relations.get_folder_ids_for_document(
                tenant=identity.tenant,
                document_id=identity.document_id,
            )
            signal_folder_ids = (
                await tx.folder_projections.folder_ids_with_signals_referencing_document(
                    document_id=identity.document_id,
                )
            )
            affected_folder_ids = await tx.folder_sources.ancestor_folder_ids(
                tenant=identity.tenant,
                folder_ids=tuple(sorted({*direct_folder_ids, *signal_folder_ids})),
            )
            await tx.document_projections.mark_document_projection_deleted(
                tenant=identity.tenant,
                document_id=identity.document_id,
            )
            await tx.document_relations.delete_for_document(
                tenant=identity.tenant,
                document_id=identity.document_id,
            )
            await tx.document_sources.mark_document_source_deleted(
                tenant=identity.tenant,
                document_id=identity.document_id,
            )
            invalidations = await FolderSignalInvalidationService().invalidate(
                tx=tx,
                tenant=identity.tenant,
                folder_ids=affected_folder_ids,
            )

        sql = _all_sql(connection)
        self.assertEqual(identity.tenant, "tenant-1")
        self.assertEqual(identity.source_version, "source-v1")
        self.assertEqual(affected_folder_ids, ("folder-1", "folder-2"))
        self.assertTrue(
            any(
                isinstance(param, datetime)
                for _, params in connection.calls
                for param in params
            )
        )
        self.assertNotIn("document_type = %s", sql)
        self.assertNotIn("IS NULL OR document_type", sql)
        self.assertIn("DELETE FROM folder_signals", sql)
        self.assertIn("folder_id IN", sql)
        self.assertIn("UPDATE folder_index_records", sql)
        self.assertIn("FROM source_document_folder_relations", sql)
        self.assertIn("DELETE FROM source_document_folder_relations", sql)
        self.assertNotIn("source_document_folder_relation_state", sql)
        self.assertNotIn("related_document_id = NULL", sql)
        params = [params for _, params in connection.calls]
        self.assertEqual(
            params[:4],
            [
                ("doc-1",),
                ("tenant-1", "doc-1"),
                ("doc-1",),
                ("tenant-1", "folder-1", "folder-2", "tenant-1"),
            ],
        )
        self.assertIn(("folder-1", "folder-2"), params)
        source_delete_index = _first_sql_index(connection, "UPDATE document_sources")
        folder_signal_delete_index = _first_sql_index(
            connection,
            "DELETE FROM folder_signals",
        )
        folder_pending_index = _first_sql_index(
            connection,
            "UPDATE folder_index_records",
        )
        self.assertLess(source_delete_index, folder_signal_delete_index)
        self.assertLess(folder_signal_delete_index, folder_pending_index)
        self.assertEqual(
            [
                (invalidation.folder_id, invalidation.signal_generation_version)
                for invalidation in invalidations
            ],
            [("folder-1", "1"), ("folder-2", "1")],
        )
        self.assertTrue(any("folder-1" in call_params for call_params in params))
        self.assertTrue(any("folder-2" in call_params for call_params in params))

    async def test_document_source_and_projection_repositories_read_recommendation_context(
        self,
    ) -> None:
        connection = FakeConnection(
            row_sets=[
                [
                    (
                        _document_source_row(
                            tenant="tenant-1",
                            document_type="document",
                            document_id="doc-1",
                            source_version="v2",
                            title="Indexed title",
                            source_created_at="2026-05-18T10:00:00+09:00",
                            source_updated_at="2026-05-18T11:00:00+09:00",
                            metadata_json={"source": "metadata"},
                        ),
                    )
                ],
                [
                    (
                        _document_source_row(
                            tenant="tenant-1",
                            document_type="document",
                            document_id="doc-1",
                            source_version="v2",
                            title="Indexed title",
                            source_created_at="2026-05-18T10:00:00+09:00",
                            source_updated_at="2026-05-18T11:00:00+09:00",
                            metadata_json={"source": "metadata"},
                        ),
                    )
                ],
                [
                    (
                        _document_signal_row(
                            signal_id="signal-concept",
                            signal_type="concept",
                            signal_key="concept-b",
                            text="Concept text",
                            confidence=0.9,
                        ),
                    ),
                    (
                        _document_signal_row(
                            signal_id="signal-summary",
                            signal_type="summary",
                            signal_key="summary-a",
                            text="Summary text",
                            confidence=0.4,
                        ),
                    ),
                    (
                        _document_signal_row(
                            signal_id="signal-entity",
                            signal_type="entity",
                            signal_key="entity-a",
                            text="Entity text",
                            confidence=None,
                        ),
                    ),
                ],
            ]
        )

        source = await _document_source_repository(
            connection,
        ).get_current_document_source(tenant="tenant-1", document_id="doc-1")
        signal_texts = await _document_projection_repository(
            connection,
        ).get_document_signal_texts(tenant="tenant-1", document_id="doc-1")

        self.assertIsNotNone(source)
        self.assertEqual(source.tenant, "tenant-1")
        self.assertEqual(source.document_type, "document")
        self.assertEqual(source.document_id, "doc-1")
        self.assertEqual(source.source_version, "v2")
        self.assertEqual(source.title, "Indexed title")
        self.assertEqual(source.metadata, {"source": "metadata"})
        self.assertEqual(signal_texts, ("Summary text", "Concept text", "Entity text"))
        self.assertNotIn("is_current = true", _all_sql(connection))
        self.assertIn("document_sources.document_id = %s", _all_sql(connection))
        self.assertNotIn("status = 'indexed'", _all_sql(connection))
        self.assertIn("FROM document_signals", _all_sql(connection))
        self.assertNotIn("scope_type = 'document'", _all_sql(connection))
        params = [params for _, params in connection.calls]
        self.assertEqual(params[0][0:2], ("tenant-1", "doc-1"))
        self.assertEqual(params[1][0:2], ("tenant-1", "doc-1"))

    async def test_document_projection_current_reads_require_current_source(
        self,
    ) -> None:
        connection = FakeConnection(
            row_sets=[
                [(1,)],
                [(1,)],
                [(1,)],
                [
                    (
                        _document_signal_row(
                            signal_id="signal-summary",
                            signal_type="summary",
                            signal_key="summary-a",
                            text="Summary text",
                            confidence=0.4,
                        ),
                    )
                ],
            ]
        )

        has_index = await _document_projection_repository(
            connection,
        ).has_current_document_index(tenant="tenant-1", document_id="doc-1")
        signal_texts = await _document_projection_repository(
            connection,
        ).get_document_signal_texts(tenant="tenant-1", document_id="doc-1")

        self.assertTrue(has_index)
        self.assertEqual(signal_texts, ("Summary text",))
        sql = _all_sql(connection)
        self.assertEqual(sql.count("document_sources.deleted_at IS NULL"), 2)

    async def test_document_index_record_freshness_reads_require_current_source(
        self,
    ) -> None:
        connection = FakeConnection(row_sets=[[(1,)], [(1,)], [(1,)], [(1,)]])
        checker = PostgresSourceFreshnessChecker(
            sessions=_postgres_sessions(connection),
        )

        index_is_current = await checker.is_current_document_index_input_digest(
            tenant="tenant-1",
            document_id="doc-1",
            document_index_input_digest="document-index-input-digest",
        )
        signal_is_current = await checker.is_current_document_signal_input_digest(
            tenant="tenant-1",
            document_id="doc-1",
            document_signal_input_digest="document-signal-input-digest",
            signal_generation_version="signal-generation-v1",
        )

        self.assertTrue(index_is_current)
        self.assertTrue(signal_is_current)
        sql = _all_sql(connection)
        self.assertEqual(sql.count("document_sources.deleted_at IS NULL"), 2)
        self.assertNotIn("JOIN document_sources", sql)

    async def test_document_relation_repository_reads_current_folder_relations(
        self,
    ) -> None:
        connection = FakeConnection(row_sets=[[("folder-current",)]])

        folder_ids = await _document_relation_repository(
            connection,
        ).get_folder_ids_for_document(tenant="tenant-1", document_id="doc-1")

        self.assertEqual(folder_ids, ("folder-current",))
        self.assertIn(
            "FROM source_document_folder_relations",
            _all_sql(connection),
        )
        self.assertEqual(
            [params[0:2] for _, params in connection.calls],
            [("tenant-1", "doc-1")],
        )

    async def test_folder_projection_repository_reads_signal_folder_ids_for_document(
        self,
    ) -> None:
        connection = FakeConnection(
            row_sets=[
                [("stale-signal-folder",)],
            ]
        )

        folder_ids = await _folder_projection_repository(
            connection,
        ).folder_ids_with_signals_referencing_document(
            document_id="doc-1",
        )

        sql = _all_sql(connection)
        self.assertEqual(
            folder_ids,
            ("stale-signal-folder",),
        )
        self.assertIn("folder_signals.related_document_id", sql)

    async def test_folder_signal_digest_reads_subtree_document_members(self) -> None:
        source_row = _document_source_row(
            tenant="tenant-1",
            document_id="doc-child",
            source_version="source-v1",
        )
        connection = FakeConnection(
            row_sets=[
                [(_folder_source_row(folder_id="parent-folder"),)],
                [("1",)],
                [("child-folder",), ("parent-folder",)],
                [("doc-child",)],
                [(source_row,)],
                [],
            ]
        )

        async with _postgres_indexing_write_sessions(connection).transaction() as tx:
            record = await FolderSignalInvalidationService().folder_index_record(
                tx=tx,
                tenant="tenant-1",
                folder_id="parent-folder",
            )

        sql = _all_sql(connection)
        self.assertNotEqual(record.folder_signal_input_digest, "")
        self.assertIn("WITH RECURSIVE subtree_folders", sql)
        self.assertIn("folder_sources_1.parent_folder_id = subtree_folders.folder_id", sql)
        self.assertIn("SELECT DISTINCT source_document_folder_relations.document_id", sql)
        self.assertIn("document_sources.deleted_at IS NULL", sql)
        self.assertIn("document_index_records.deleted_at IS NULL", sql)

    async def test_folder_signal_invalidation_reads_subtree_document_members(
        self,
    ) -> None:
        source_row = _document_source_row(
            tenant="tenant-1",
            document_id="doc-child",
            source_version="source-v1",
        )
        connection = FakeConnection(
            row_sets=[
                [(_folder_source_row(folder_id="parent-folder"),)],
                [("1",)],
                [("child-folder",), ("parent-folder",)],
                [("doc-child",)],
                [(source_row,)],
                [],
                [("parent-folder",)],
            ]
        )

        async with _postgres_indexing_write_sessions(connection).transaction() as tx:
            invalidations = await FolderSignalInvalidationService().invalidate(
                tx=tx,
                tenant="tenant-1",
                folder_ids=("parent-folder",),
            )

        sql = _all_sql(connection)
        self.assertEqual(len(invalidations), 1)
        self.assertIn("WITH RECURSIVE subtree_folders", sql)
        self.assertIn("SELECT DISTINCT source_document_folder_relations.document_id", sql)
        self.assertIn("DELETE FROM folder_signals", sql)
        self.assertIn("UPDATE folder_index_records", sql)

    async def test_document_source_repository_returns_none_without_current_source(
        self,
    ) -> None:
        connection = FakeConnection(row_sets=[[]])

        source = await _document_source_repository(
            connection,
        ).get_current_document_source(tenant="tenant-1", document_id="doc-1")

        self.assertIsNone(source)
        self.assertEqual(
            [params[0:2] for _, params in connection.calls],
            [("tenant-1", "doc-1")],
        )

    async def test_indexing_write_session_writes_folder_ref_by_global_folder_id(
        self,
    ) -> None:
        connection = FakeConnection()

        async with _postgres_indexing_write_sessions(connection).transaction() as tx:
            folder = _sample_source_folder()
            await tx.folder_sources.upsert_folder_source(folder)
            await tx.folder_projections.upsert_folder_index_record(
                record=FolderIndexState(
                    folder_id=folder.folder_id,
                    folder_index_input_digest="folder-index-input-v1",
                    folder_signal_input_digest="folder-signal-input-v1",
                    signal_generation_version="1",
                ),
            )

        sql = _all_sql(connection)
        self.assertIn("INSERT INTO folder_sources", sql)
        self.assertIn("ON CONFLICT (folder_id)", sql)
        self.assertIn("source_created_at", sql)
        self.assertIn("source_updated_at", sql)
        self.assertNotIn("substring(folder_sources.source_version", sql)
        self.assertNotIn("substring(excluded.source_version", sql)
        self.assertIn(
            "where folder_sources.source_version = excluded.source_version "
            "or folder_sources.source_updated_at < excluded.source_updated_at",
            sql.lower(),
        )
        self.assertNotIn("ON CONFLICT (tenant_id, folder_id)", sql)
        self.assertNotIn("name_digest", sql)
        self.assertNotIn("path_digest", sql)
        self.assertNotIn("parent_folder_id_digest", sql)

    async def test_folder_source_upsert_only_persists_source_and_checks_freshness(
        self,
    ) -> None:
        connection = FakeConnection(
            row_sets=[
                [(1,)],
            ]
        )
        folder = SourceFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v2",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-03T11:00:00+09:00",
            name="Architecture",
            path="/New/Architecture",
            parent_folder_id="new-parent",
            description="Architecture notes.",
            metadata={"source": "test"},
        )

        async with _postgres_indexing_write_sessions(connection).transaction() as tx:
            source_is_current = await tx.folder_sources.upsert_folder_source(folder)

        sql = _all_sql(connection)
        self.assertTrue(source_is_current)
        self.assertIn("INSERT INTO folder_sources", sql)
        self.assertNotIn("WITH RECURSIVE ancestor_folders", sql)

    async def test_folder_signal_refresh_does_not_replace_rows_when_digest_is_stale(
        self,
    ) -> None:
        connection = FakeConnection(
            row_sets=[
                [(1,)],
                [("folder-signal-input-v1",)],
                [],
            ],
        )

        async with _postgres_indexing_write_sessions(connection).transaction() as tx:
            applied = await tx.folder_projections.replace_folder_signals(
                folder=_sample_source_folder(),
                signals=(_sample_folder_signal(),),
                expected_folder_signal_input_digest="folder-signal-input-v1",
                signal_generation_version="1",
            )

        sql = _all_sql(connection)
        self.assertFalse(applied)
        self.assertIn("UPDATE folder_index_records", sql)
        self.assertNotIn("DELETE FROM folder_signals", sql)
        self.assertNotIn("INSERT INTO folder_signals", sql)

    async def test_folder_signal_refresh_locks_digest_before_replacing_rows(
        self,
    ) -> None:
        connection = FakeConnection(
            row_sets=[
                [(1,)],
                [("folder-signal-input-v1",)],
                [("folder-signal-input-v1",)],
            ],
        )

        async with _postgres_indexing_write_sessions(connection).transaction() as tx:
            applied = await tx.folder_projections.replace_folder_signals(
                folder=_sample_source_folder(),
                signals=(_sample_folder_signal(),),
                expected_folder_signal_input_digest="folder-signal-input-v1",
                signal_generation_version="1",
            )

        self.assertTrue(applied)
        self.assertLess(
            _first_sql_index(connection, "UPDATE folder_index_records"),
            _first_sql_index(connection, "DELETE FROM folder_signals"),
        )
        self.assertLess(
            _first_sql_index(connection, "DELETE FROM folder_signals"),
            _first_sql_index(connection, "INSERT INTO folder_signals"),
        )

    def test_folder_index_digest_tracks_hierarchy_and_metadata_inputs(self) -> None:
        digest_service = FolderProjectionDigestService()
        source = SourceFolder(
            tenant="tenant-1",
            folder_id="folder-1",
            source_version="folder-v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            name="Founding",
            parent_folder_id="root",
            description="Founder resources",
            metadata={"scope": "research"},
        )

        digest = digest_service.folder_index_input_digest(
            folder_id="folder-1",
            folder=source,
        )
        parent_changed = digest_service.folder_index_input_digest(
            folder_id="folder-1",
            folder=replace(source, parent_folder_id="archive"),
        )
        metadata_changed = digest_service.folder_index_input_digest(
            folder_id="folder-1",
            folder=replace(source, metadata={"scope": "operations"}),
        )
        version_changed = digest_service.folder_index_input_digest(
            folder_id="folder-1",
            folder=replace(source, source_version="folder-v2"),
        )

        self.assertNotEqual(digest, parent_changed)
        self.assertNotEqual(digest, metadata_changed)
        self.assertEqual(digest, version_changed)

    async def test_projection_ledger_records_vector_projection(
        self,
    ) -> None:
        connection = FakeConnection()
        repository = _projection_ledger_repository(connection)

        await repository.record_document_vector_projected(
            record=VectorProjectionState(
                tenant="tenant-1",
                collection_name="documents",
                point_id="11111111-1111-4111-8111-111111111111",
                source_kind="document",
                source_id="doc-1",
                vector_item_kind="document",
                vector_item_id="doc-1",
                source_input_digest="source-input-v1",
                vector_input_digest="vector-input-v1",
            ),
        )

        sql = _all_sql(connection)
        self.assertIn("INSERT INTO vector_projection_records", sql)
        self.assertNotIn("INSERT INTO vector_collections", sql)
        self.assertNotIn("INSERT INTO tenant_vector_collection_bindings", sql)
        self.assertNotIn("status = 'active'", sql)
        self.assertNotIn("role = 'active'", sql)
        self.assertNotIn("activated_at", sql)
        self.assertNotIn("deprecated_at IS NULL", sql)
        self.assertNotIn("aggregate_kind", sql)
        self.assertNotIn("aggregate_id", sql)
        self.assertNotIn("subject_id", sql)
        self.assertNotIn("source_version", sql)
        self.assertNotIn("payload_digest", sql)
        self.assertNotIn("projected_at", sql)
        self.assertIn(
            "source_kind,",
            sql,
        )
        self.assertIn("vector_item_id", sql)
        self.assertIn("point_id = excluded.point_id", sql.lower())
        self.assertIn("source_input_digest = excluded.source_input_digest", sql.lower())
        self.assertIn("vector_input_digest = excluded.vector_input_digest", sql.lower())
        self.assertNotIn("ON CONFLICT (collection_name, point_id)", sql)
        self.assertNotIn("document_index_id", sql)
        self.assertEqual(
            connection.calls[-1][1][0:4],
            (
                "tenant-1",
                "documents",
                "11111111-1111-4111-8111-111111111111",
                "document",
            ),
        )
        self.assertEqual(
            connection.calls[-1][1][4:],
            ("doc-1", "document", "doc-1", "source-input-v1", "vector-input-v1"),
        )

    async def test_projection_ledger_replaces_chunk_vectors_in_one_transaction(
        self,
    ) -> None:
        connection = TransactionalFakeConnection(
            fail_on_sql="INSERT INTO vector_projection_records",
        )

        with self.assertRaises(RuntimeError):
            async with _postgres_projection_ledger_sessions(
                connection
            ).transaction() as session:
                await session.projection_ledger.replace_chunk_vector_records(
                    tenant="tenant-1",
                    document_id="doc-1",
                    records=(
                        VectorProjectionState(
                            tenant="tenant-1",
                            collection_name="chunks",
                            point_id="22222222-2222-4222-8222-222222222222",
                            source_kind="document",
                            source_id="doc-1",
                            vector_item_kind="chunk",
                            vector_item_id="chunk-1",
                            source_input_digest="source-input-v1",
                            vector_input_digest="vector-input-v1",
                        ),
                    ),
                )

        sql = _all_sql(connection)
        self.assertIn("DELETE FROM vector_projection_records", sql)
        self.assertIn("INSERT INTO vector_projection_records", sql)
        self.assertEqual(connection.rollback_count, 1)
        self.assertEqual(connection.committed_calls, [])

    async def test_projection_ledger_deletes_document_projections_by_document_id(
        self,
    ) -> None:
        connection = FakeConnection()
        repository = _projection_ledger_repository(connection)

        await repository.delete_document_vector_records(
            tenant="tenant-1",
            document_id="doc-1",
        )
        await repository.delete_chunk_vector_records(
            tenant="tenant-1",
            document_id="doc-1",
        )
        await repository.delete_signal_vector_records(
            tenant="tenant-1",
            document_id="doc-1",
        )
        await repository.delete_folder_signal_vector_records(
            tenant="tenant-1",
            folder_id="folder-1",
        )
        await repository.delete_folder_vector_records(
            tenant="tenant-1",
            folder_id="folder-1",
        )
        await repository.delete_stale_folder_signal_vector_records(
            tenant="tenant-1",
            folder_id="folder-1",
            current_source_input_digest="folder-signal-input-v2",
        )

        self.assertEqual(
            [params for _, params in connection.calls],
            [
                ("tenant-1", "document", "doc-1", "document"),
                ("tenant-1", "document", "doc-1", "chunk"),
                ("tenant-1", "document", "doc-1", "signal"),
                ("tenant-1", "folder", "folder-1", "signal"),
                ("tenant-1", "folder", "folder-1", "folder"),
                (
                    "tenant-1",
                    "folder",
                    "folder-1",
                    "signal",
                    "folder-signal-input-v2",
                ),
            ],
        )
        self.assertIn("DELETE FROM vector_projection_records", _all_sql(connection))
        self.assertIn("source_input_digest != %s", _all_sql(connection))
        self.assertNotIn("SET deleted_at", _all_sql(connection))

    async def test_outbox_repository_appends_event_with_debezium_key_fields(self) -> None:
        connection = FakeConnection()
        repository = outbox.OutboxRepository(
            outbox_events=OutboxEventStore(connection),
        )
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v1",
        )

        await repository.append(event)

        self.assertEqual(len(connection.calls), 1)
        sql, params = connection.calls[0]
        self.assertIn("outbox_events", sql)
        self.assertEqual(params[1], "tenant-1")
        self.assertEqual(params[2], "document")
        self.assertEqual(params[3], "doc-1")
        self.assertEqual(params[4], "DOCUMENT_DELETED")
        self.assertEqual(params[5], 1)
        self.assertEqual(params[6], event.idempotency_key)
        self.assertEqual(
            params[7],
            {
                "tenant": "tenant-1",
                "document_id": "doc-1",
                "affected_folder_ids": [],
            },
        )
        self.assertEqual(event.partition_key, "document:tenant-1:doc-1")

    async def test_indexing_write_session_writes_projection_and_outbox_in_one_connection(
        self,
    ) -> None:
        connection = FakeConnection()
        index_record = _sample_document_index_record()
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v1",
        )
        indexing = _postgres_indexing_write_sessions(connection)

        async with indexing.transaction() as tx:
            await _write_sample_document_index(
                tx,
                index_record=index_record,
            )
            await tx.outbox.append(event)

        sql = _all_sql(connection)
        self.assertIn("INSERT INTO document_sources", sql)
        self.assertNotIn("INSERT INTO source_document_snapshots", sql)
        self.assertIn("INSERT INTO document_index_records", sql)
        self.assertNotIn("INSERT INTO document_chunk_sets", sql)
        self.assertIn("INSERT INTO document_chunks", sql)
        self.assertIn("INSERT INTO document_signals", sql)
        self.assertIn("INSERT INTO outbox_events", sql)

    async def test_indexing_write_session_rolls_back_projection_when_outbox_insert_fails(
        self,
    ) -> None:
        connection = TransactionalFakeConnection(fail_on_outbox=True)
        index_record = _sample_document_index_record()
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v1",
        )
        indexing = _postgres_indexing_write_sessions(connection)

        with self.assertRaisesRegex(RuntimeError, "outbox insert failed"):
            async with indexing.transaction() as tx:
                await _write_sample_document_index(
                    tx,
                    index_record=index_record,
                )
                await tx.outbox.append(event)

        self.assertEqual(connection.rollback_count, 1)
        self.assertEqual(connection.committed_calls, [])
        self.assertIn("INSERT INTO document_index_records", _all_sql(connection))
        self.assertIn("INSERT INTO outbox_events", _all_sql(connection))

    async def test_task_repository_rebuilds_snapshot_from_normalized_rows(self) -> None:
        task_input_id = "task-input-1"
        request_text = "Draft a plan."
        request_context = TaskContext(
            requested_at="2026-05-17T09:30:00+09:00",
            document_id="doc-context",
            folder_id="folder-context",
        )
        request_entry = TaskInputEntry(
            task_input_id=task_input_id,
            task_id=TASK_ID,
            input_text=request_text,
            context=request_context,
            position=0,
        )
        final_result = TaskFinalResult(
            result_type=TaskOutputType.SUMMARY,
            result=GeneratedTextResult(text="Done."),
            title="Summary",
            metadata={"visible": True},
        )
        search_result = DocumentSearchResult(
            items=[
                DocumentRecommendation(
                    document=RetrievedDocument(
                        tenant="tenant-1",
                        document_type="document",
                        document_id="doc-1",
                        source_version="v1",
                    ),
                    score=0.9,
                    reason="Document matches the search request.",
                )
            ]
        )
        job = TaskJob(
            job_id=JOB_ID,
            job_type="find_documents",
            round_index=0,
            position=0,
            status=TaskJobStatus.SUCCEEDED,
            reason="Find matching documents.",
            input={"options": {"limit": 5}},
            started_at="2026-05-17T09:30:01+00:00",
            finished_at="2026-05-17T09:30:02+00:00",
            metadata={"artifacts_written": ["document_search_result"]},
            results=[
                TaskJobResult(
                    job_result_id=OUTPUT_ID,
                    result_type=str(TaskOutputType.SUMMARY),
                    result=final_result.result,
                    summary={"text": "Done."},
                    metadata={"visible": True},
                ),
                TaskJobResult(
                    job_result_id=SEARCH_OUTPUT_ID,
                    result_type=str(TaskOutputType.DOCUMENT_SEARCH_RESULT),
                    result=search_result,
                    summary={"count": 1},
                ),
            ],
        )
        action = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create folder",
            input=CreateFolderInput(name="Plans"),
            action_id=ACTION_ID,
            job_id=JOB_ID,
            reason="Needed for organization.",
            status=HostActionStatus.READY,
            attempts=1,
            policy=HostActionPolicy(
                max_attempts=2,
                allow_skip=True,
                retryable=True,
                requires_confirmation=False,
            ),
            metadata={"priority": "high"},
        )
        event = TaskEvent(
            event_id=EVENT_ID,
            event_type=TaskEventType.COMPLETED,
            message="Task completed.",
            job_id=JOB_ID,
            data={"ok": True},
        )
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request=request_text,
            context=request_context,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
            inputs=[request_entry],
            jobs=[job],
            result=final_result,
            host_actions=[action],
            current_action_id=action.action_id,
            events=[event],
            metadata={"workflow_round": 1},
        )
        connection = FakeConnection(
            row_sets=[
                [(task_row_from_snapshot(snapshot),)],
                [(row,) for row in task_input_rows_from_snapshot(snapshot)],
                [(row,) for row in task_job_rows_from_snapshot(snapshot)],
                [(row,) for row in task_job_result_rows_from_snapshot(snapshot)],
                [(row,) for row in host_action_rows_from_snapshot(snapshot)],
                [(row,) for row in task_event_rows_from_snapshot(snapshot)],
            ]
        )
        repository = _task_repository(connection)

        await repository.create(snapshot)
        loaded = await repository.get(task_id=TASK_ID)

        self.assertEqual(loaded, snapshot)
        self.assertIn("INSERT INTO tenant_storage_scopes", _all_sql(connection))
        self.assertIn("task_inputs", _all_sql(connection))
        self.assertIn("task_jobs", _all_sql(connection))
        self.assertIn("task_job_results", _all_sql(connection))
        self.assertNotIn("task_outputs", _all_sql(connection))
        self.assertIn("host_actions", _all_sql(connection))
        self.assertNotIn("host_action_dependencies", _all_sql(connection))
        self.assertIn("data_json", _all_sql(connection))
        self.assertNotIn("snapshot_json", _all_sql(connection))
        self.assertNotIn("event_json", _all_sql(connection))

    async def test_task_repository_rejects_malformed_text_and_metadata_rows(self) -> None:
        malformed_current_action = FakeConnection(
            row_sets=[
                [
                    (
                        TaskRow(
                            task_id=TASK_ID,
                            tenant="tenant-1",
                            request_text="Summarize this.",
                            context_json={"requested_at": "2026-05-17T09:30:00+09:00"},
                            status=str(TaskStatus.CLARIFICATION_REQUIRED),
                            analysis_message="Planning.",
                            result_type=None,
                            result_json=None,
                            result_title=None,
                            result_metadata={},
                            current_action_id=123,
                            error_json=None,
                            metadata_json={},
                        ),
                    )
                ],
                [],
                [],
                [],
                [],
                [],
            ]
        )
        with self.assertRaisesRegex(ValueError, "current_action_id"):
            await _task_repository(malformed_current_action).get(task_id=TASK_ID)

        malformed_metadata = FakeConnection(
            row_sets=[
                [
                    (
                        TaskRow(
                            task_id=TASK_ID,
                            tenant="tenant-1",
                            request_text="Summarize this.",
                            context_json={"requested_at": "2026-05-17T09:30:00+09:00"},
                            status=str(TaskStatus.CLARIFICATION_REQUIRED),
                            analysis_message="Planning.",
                            result_type=None,
                            result_json=None,
                            result_title=None,
                            result_metadata={},
                            current_action_id=None,
                            error_json=None,
                            metadata_json=[],
                        ),
                    )
                ],
                [],
                [],
                [],
                [],
                [],
            ]
        )
        with self.assertRaisesRegex(ValueError, "metadata fields"):
            await _task_repository(malformed_metadata).get(task_id=TASK_ID)

    async def test_task_repository_preserves_terminal_completion_time_after_reopen(
        self,
    ) -> None:
        connection = FakeConnection(row_sets=[[("revision-1",)]])
        repository = _task_repository(connection)
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Revise the plan.",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message="Task accepted for workflow planning."),
        )

        await repository.create(snapshot)

        sql = _all_sql(connection)
        self.assertIn(
            "completed_at = coalesce(tasks.completed_at, excluded.completed_at)",
            sql.lower(),
        )
        self.assertNotIn("excluded.status in", sql.lower())
        self.assertNotIn("case when", sql.lower())
        self.assertNotIn("ELSE false", sql)

    async def test_task_repository_save_if_unchanged_locks_before_replacing_snapshot(
        self,
    ) -> None:
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Revise the plan.",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message="Task accepted for workflow planning."),
        )
        stale_connection = FakeConnection(row_sets=[[("revision-2",)], []])

        stale_saved = await _task_repository(stale_connection).save_if_unchanged(
            snapshot,
            expected_snapshot=snapshot,
        )

        self.assertFalse(stale_saved)
        self.assertIn("FOR UPDATE", _all_sql(stale_connection))
        self.assertNotIn("INSERT INTO tasks", _all_sql(stale_connection))

        current_connection = FakeConnection(
            row_sets=[
                [("revision-1",)],
                [(task_row_from_snapshot(snapshot),)],
                [],
                [],
                [],
                [],
                [],
            ]
        )
        current_saved = await _task_repository(current_connection).save_if_unchanged(
            snapshot,
            expected_snapshot=snapshot,
        )

        self.assertTrue(current_saved)
        self.assertIn("FOR UPDATE", _all_sql(current_connection))
        self.assertIn("INSERT INTO tasks", _all_sql(current_connection))

    async def test_task_repository_create_rolls_back_when_normalized_write_fails(
        self,
    ) -> None:
        connection = TransactionalFakeConnection(fail_on_sql="INSERT INTO host_actions")
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Create a folder.",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
            status=TaskStatus.READY_FOR_HOST_ACTION,
            analysis=TaskAnalysis(message="Task is ready for host action."),
            host_actions=[
                HostAction(
                    action_type=HostActionType.CREATE_FOLDER,
                    summary="Create folder",
                    input=CreateFolderInput(name="Plans"),
                    action_id=ACTION_ID,
                )
            ],
            current_action_id=ACTION_ID,
        )

        with self.assertRaisesRegex(RuntimeError, "host action insert failed"):
            async with _postgres_task_sessions(connection).transaction() as session:
                await session.tasks.create(snapshot)

        self.assertEqual(connection.rollback_count, 1)
        self.assertEqual(connection.committed_calls, [])
        self.assertIn("INSERT INTO tasks", _all_sql(connection))
        self.assertIn("INSERT INTO host_actions", _all_sql(connection))


class PostgresAsyncAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_indexing_write_session_async_writes_index_record_and_outbox(
        self,
    ) -> None:
        connection = AsyncTransactionalFakeConnection()
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v1",
        )
        indexing = _postgres_indexing_write_sessions(connection)

        async with indexing.transaction() as tx:
            await _write_sample_document_index(tx)
            await tx.outbox.append(event)

        sql = _all_sql(connection)
        self.assertIn("INSERT INTO document_sources", sql)
        self.assertIn("INSERT INTO document_index_records", sql)
        self.assertIn("INSERT INTO document_chunks", sql)
        self.assertIn("INSERT INTO document_signals", sql)
        self.assertIn("INSERT INTO outbox_events", sql)
        self.assertEqual(connection.rollback_count, 0)
        self.assertEqual(connection.committed_calls, connection.calls)

    async def test_indexing_write_session_async_rolls_back_on_outbox_failure(
        self,
    ) -> None:
        connection = AsyncTransactionalFakeConnection(fail_on_outbox=True)
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
            source_version="v1",
        )
        indexing = _postgres_indexing_write_sessions(connection)

        with self.assertRaisesRegex(RuntimeError, "outbox insert failed"):
            async with indexing.transaction() as tx:
                await _write_sample_document_index(tx)
                await tx.outbox.append(event)

        self.assertEqual(connection.rollback_count, 1)
        self.assertEqual(connection.committed_calls, [])
        self.assertIn("INSERT INTO document_index_records", _all_sql(connection))
        self.assertIn("INSERT INTO outbox_events", _all_sql(connection))

    async def test_document_source_and_projection_repositories_read_current_source(
        self,
    ) -> None:
        connection = AsyncFakeConnection(
            row_sets=[
                [
                    (
                        _document_source_row(
                            tenant="tenant-1",
                            document_type="document",
                            document_id="doc-1",
                            source_version="v2",
                            title="Indexed title",
                            source_created_at="2026-05-18T10:00:00+09:00",
                            source_updated_at="2026-05-18T11:00:00+09:00",
                            metadata_json={"source": "metadata"},
                        ),
                    )
                ],
                [
                    (
                        _document_source_row(
                            tenant="tenant-1",
                            document_type="document",
                            document_id="doc-1",
                            source_version="v2",
                            title="Indexed title",
                            source_created_at="2026-05-18T10:00:00+09:00",
                            source_updated_at="2026-05-18T11:00:00+09:00",
                            metadata_json={"source": "metadata"},
                        ),
                    )
                ],
                [
                    (
                        _document_signal_row(
                            signal_id="signal-concept",
                            signal_type="concept",
                            signal_key="concept-b",
                            text="Concept text",
                            confidence=0.9,
                        ),
                    ),
                    (
                        _document_signal_row(
                            signal_id="signal-summary",
                            signal_type="summary",
                            signal_key="summary-a",
                            text="Summary text",
                            confidence=0.4,
                        ),
                    ),
                ],
            ]
        )

        source = await _document_source_repository(
            connection,
        ).get_current_document_source(tenant="tenant-1", document_id="doc-1")
        signal_texts = await _document_projection_repository(
            connection,
        ).get_document_signal_texts(tenant="tenant-1", document_id="doc-1")

        self.assertIsNotNone(source)
        self.assertEqual(signal_texts, ("Summary text", "Concept text"))
        params = [params for _, params in connection.calls]
        self.assertEqual(params[0][0:2], ("tenant-1", "doc-1"))
        self.assertEqual(params[1][0:2], ("tenant-1", "doc-1"))

    async def test_document_source_repository_searches_titles_by_keyword(self) -> None:
        source_row = _document_source_row(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            source_created_at="2026-05-01T10:00:00+09:00",
            source_updated_at="2026-05-02T11:00:00+09:00",
            metadata_json={"source": "test"},
        )
        connection = AsyncFakeConnection(
            row_sets=[
                [(source_row, 0.25)],
            ]
        )

        results = await _document_source_repository(connection).search_titles_by_keyword(
            tenant="tenant-1",
            query_text="useful document",
            top_k=5,
            document_type=None,
            document_id=None,
            document_ids=("doc-1",),
            created_at=None,
            updated_at=None,
            metadata_filter=None,
        )

        source, score = results[0]
        self.assertEqual(source.document_id, "doc-1")
        self.assertEqual(score, 0.25)
        self.assertIn("title_search_vector", _all_sql(connection))

    async def test_folder_source_repository_searches_name_and_description_keywords(
        self,
    ) -> None:
        folder_row = _folder_source_row(
            tenant="tenant-1",
            folder_id="folder-1",
            name="Startup",
            description="Founder notes",
        )
        connection = AsyncFakeConnection(
            row_sets=[
                [(folder_row, 0.4)],
                [(folder_row, 0.2)],
            ]
        )

        name_results = await _folder_source_repository(
            connection,
        ).search_names_by_keyword(
            tenant="tenant-1",
            query_text="startup",
            top_k=5,
            folder_ids=("folder-1",),
            created_at=None,
            updated_at=None,
        )
        description_results = await _folder_source_repository(
            connection,
        ).search_descriptions_by_keyword(
            tenant="tenant-1",
            query_text="founder",
            top_k=5,
            folder_ids=("folder-1",),
            created_at=None,
            updated_at=None,
        )

        sql = _all_sql(connection)
        self.assertIn("folder_sources.name_search_vector @@", sql)
        self.assertIn("folder_sources.description_search_vector @@", sql)
        self.assertEqual(name_results[0][0].folder_id, "folder-1")
        self.assertEqual(name_results[0][1], 0.4)
        self.assertEqual(description_results[0][0].folder_id, "folder-1")
        self.assertEqual(description_results[0][1], 0.2)


def _all_sql(connection: Any) -> str:
    return "\n".join(sql for sql, _ in connection.calls)


def _first_sql_index(connection: Any, fragment: str) -> int:
    return next(
        index for index, (sql, _) in enumerate(connection.calls) if fragment in sql
    )


def _compiled_sql(
    statement: Executable | str,
    params: Any = None,
) -> tuple[str, tuple[Any, ...]]:
    if isinstance(statement, str):
        return statement, tuple(params or ())

    compiled = statement.compile(
        dialect=postgresql.dialect(paramstyle="format"),
        compile_kwargs={"render_postcompile": True},
    )
    param_names = getattr(compiled, "positiontup", None) or tuple(compiled.params)
    return str(compiled), tuple(compiled.params[name] for name in param_names)


def _orm_insert_values(instance: Any) -> dict[str, Any]:
    return {
        key: value
        for key, value in vars(instance).items()
        if not key.startswith("_")
    }


def _driver_sql_to_percent(sql: str) -> str:
    converted = sql
    for index in range(1, sql.count("$") + 1):
        converted = converted.replace(f"${index}", "%s")
    return converted


def _document_source_repository(
    connection: Any,
) -> document_sources.DocumentSourceRepository:
    return document_sources.DocumentSourceRepository(
        tenants=TenantStorageScopeStore(connection),
        document_sources=DocumentSourceStore(connection),
    )


def _document_projection_repository(
    connection: Any,
) -> document_projections.DocumentProjectionRepository:
    return document_projections.DocumentProjectionRepository(
        document_sources=DocumentSourceStore(connection),
        document_index_records=DocumentIndexRecordStore(connection),
        document_chunks=DocumentChunkStore(connection),
        document_signals=DocumentSignalStore(connection),
    )


def _document_relation_repository(
    connection: Any,
) -> document_relations.DocumentRelationRepository:
    return document_relations.DocumentRelationRepository(
        document_folder_relations=DocumentFolderRelationStore(connection),
    )


def _folder_projection_repository(
    connection: Any,
) -> folder_projections.FolderProjectionRepository:
    return folder_projections.FolderProjectionRepository(
        folder_sources=FolderSourceStore(connection),
        folder_index_records=FolderIndexRecordStore(connection),
        folder_signals=FolderSignalStore(connection),
    )


def _folder_source_repository(
    connection: Any,
) -> folder_sources.FolderSourceRepository:
    return folder_sources.FolderSourceRepository(
        tenants=TenantStorageScopeStore(connection),
        folder_sources=FolderSourceStore(connection),
    )


def _projection_ledger_repository(
    connection: Any,
) -> projection_ledgers.ProjectionLedgerRepository:
    return projection_ledgers.ProjectionLedgerRepository(
        vector_projection_records=VectorProjectionRecordStore(connection),
    )


def _postgres_projection_ledger_sessions(
    connection: Any,
) -> PostgresProjectionLedgerSessionProvider:
    return PostgresProjectionLedgerSessionProvider(sessions=_postgres_sessions(connection))


def _task_repository(connection: Any) -> tasks.TaskRepository:
    return tasks.TaskRepository(
        tenants=TenantStorageScopeStore(connection),
        tasks=TaskStore(connection),
        task_inputs=TaskInputStore(connection),
        task_jobs=TaskJobStore(connection),
        task_job_results=TaskJobResultStore(connection),
        host_actions=HostActionStore(connection),
        task_events=TaskEventStore(connection),
    )


def _postgres_task_sessions(connection: Any) -> PostgresTaskSessionProvider:
    return PostgresTaskSessionProvider(sessions=_postgres_sessions(connection))


def _postgres_sessions(connection: Any) -> FakePostgresSessions:
    return FakePostgresSessions(connection)


def _postgres_indexing_write_sessions(
    connection: Any,
    *,
    purge_after_days: int = 90,
) -> PostgresIndexingWriteSessionProvider:
    return PostgresIndexingWriteSessionProvider(
        sessions=_postgres_sessions(connection),
        purge_after_policy=PurgeAfterPolicy(days=purge_after_days),
    )


async def _write_sample_document_index(
    tx: Any,
    *,
    document: SourceDocument | None = None,
    chunks: tuple[DocumentChunk, ...] | None = None,
    index_record: DocumentIndexState | None = None,
    signals: tuple[DocumentSignal, ...] | None = None,
) -> None:
    document = document or _sample_source_document()
    await tx.document_sources.upsert_document_source(document)
    await tx.document_projections.replace_document_projection(
        document=document,
        chunks=chunks or (_sample_document_chunk(),),
        index_record=index_record or _sample_document_index_record(),
        signals=signals or (_sample_document_signal(),),
    )
    folder_ids = await tx.document_relations.get_folder_ids_for_document(
        tenant=document.tenant,
        document_id=document.document_id,
    )
    await FolderSignalInvalidationService().invalidate(
        tx=tx,
        tenant=document.tenant,
        folder_ids=folder_ids,
    )


def _sample_document_index_record() -> DocumentIndexState:
    return DocumentIndexState(
        document_id="doc-1",
        document_index_input_digest="index-input-v1",
        document_signal_input_digest="index-input-v1",
    )


def _document_source_row(
    *,
    tenant: str = "tenant-1",
    document_id: str = "doc-1",
    document_type: str | None = "document",
    source_version: str = "v1",
    title: str = "Document title",
    source_created_at: datetime | str = "2026-05-01T10:00:00+09:00",
    source_updated_at: datetime | str = "2026-05-02T11:00:00+09:00",
    metadata_json: dict[str, object] | None = None,
) -> DocumentSourceRow:
    return DocumentSourceRow(
        tenant_id=tenant,
        document_id=document_id,
        document_type=document_type,
        source_version=source_version,
        source_created_at=_datetime(source_created_at),
        source_updated_at=_datetime(source_updated_at),
        title=title,
        content_digest="content-digest-1",
        content_size_bytes=128,
        metadata_json=metadata_json or {},
    )


def _datetime(value: datetime | str) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _document_chunk_row(
    *,
    tenant: str = "tenant-1",
    document_id: str = "doc-1",
    document_index_input_digest: str = "index-input-v1",
    chunk_id: str = "chunk-1",
    chunk_index: int = 0,
    search_text: str = "Chunk text",
    source_start_offset: int = 0,
    source_end_offset: int = 10,
) -> DocumentChunkRow:
    return DocumentChunkRow(
        chunk_id=chunk_id,
        tenant_id=tenant,
        document_id=document_id,
        document_index_input_digest=document_index_input_digest,
        chunk_index=chunk_index,
        search_text=search_text,
        source_start_offset=source_start_offset,
        source_end_offset=source_end_offset,
    )


def _document_signal_row(
    *,
    signal_id: str = "signal-1",
    document_id: str = "doc-1",
    signal_type: str = "summary",
    signal_key: str = "summary",
    text: str = "Signal text",
    confidence: float | None = 0.9,
) -> DocumentSignalRow:
    return DocumentSignalRow(
        signal_id=signal_id,
        document_id=document_id,
        document_signal_input_digest="document-signal-input-v1",
        signal_generation_version="1",
        signal_type=signal_type,
        signal_key=signal_key,
        text=text,
        attributes_json={},
        evidence_json=[],
        confidence=confidence,
        extractor_name="extractor",
        extractor_version="v1",
        generation_model=None,
    )


def _folder_source_row(
    *,
    tenant: str = "tenant-1",
    folder_id: str = "folder-1",
    source_version: str = "folder-v1",
    name: str = "Folder",
    path: str | None = None,
    parent_folder_id: str | None = None,
    description: str = "",
    metadata_json: dict[str, object] | None = None,
) -> FolderSourceRow:
    return FolderSourceRow(
        tenant_id=tenant,
        folder_id=folder_id,
        source_version=source_version,
        source_created_at="2026-05-01T10:00:00+09:00",
        source_updated_at="2026-05-02T11:00:00+09:00",
        name=name,
        path=path,
        parent_folder_id=parent_folder_id,
        description=description,
        metadata_json=metadata_json or {},
    )


def _sample_source_document() -> SourceDocument:
    return SourceDocument(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        title="Architecture memo",
        body="A useful document.",
        metadata={"source": "test"},
    )


def _sample_folder_relation_snapshot() -> SourceDocumentFolderRelationSnapshot:
    return SourceDocumentFolderRelationSnapshot(
        tenant="tenant-1",
        document_id="doc-1",
        source_version="v1",
        folder_ids=("folder-1",),
    )


def _sample_source_folder() -> SourceFolder:
    return SourceFolder(
        tenant="tenant-1",
        folder_id="folder-1",
        source_version="folder-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        name="Architecture",
        path="/Architecture",
        parent_folder_id="root",
        description="Architecture notes.",
        metadata={"source": "test"},
    )


def _sample_document_chunk() -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        document_index_input_digest="index-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        chunk_id="11111111-1111-4111-8111-111111111111",
        chunk_index=0,
        text="A useful document.",
        start_offset=0,
        end_offset=18,
    )


def _sample_document_signal() -> DocumentSignal:
    return DocumentSignalService().create(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        document_signal_input_digest="index-input-v1",
        signal_type=DocumentSignalType.SUMMARY,
        text="A useful document.",
        attributes={},
        evidence=(DocumentSignalEvidence(chunk_id="chunk-1", quote="A useful document."),),
        confidence=0.9,
        extractor_name="test",
        extractor_version="v1",
        generation_model="model-a",
    )


def _sample_folder_signal() -> FolderSignal:
    return FolderSignalService().create(
        tenant="tenant-1",
        folder_id="folder-1",
        source_version="folder-v1",
        folder_signal_input_digest="folder-signal-input-v1",
        signal_generation_version="1",
        signal_type=FolderSignalType.SUMMARY,
        signal_key="summary",
        text="Architecture folder summary.",
        attributes={},
        evidence=(),
        confidence=0.8,
        extractor_name="test",
        extractor_version="v1",
        generation_model="model-a",
    )


if __name__ == "__main__":
    unittest.main()
