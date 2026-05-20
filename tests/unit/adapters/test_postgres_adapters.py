from __future__ import annotations

import unittest
from typing import Any

from foldmind_ai_core.adapters.outbound.domain_model_codec import domain_model_json
from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
from foldmind_ai_core.adapters.outbound.postgres.index_repository import (
    PostgresIndexRepository,
)
from foldmind_ai_core.adapters.outbound.postgres.document_keyword_search_store import (
    PostgresDocumentKeywordSearchStore,
)
from foldmind_ai_core.adapters.outbound.postgres.indexed_document_source_repository import (
    PostgresIndexedDocumentSourceRepository,
)
from foldmind_ai_core.adapters.outbound.postgres.indexing_unit_of_work import (
    PostgresIndexingUnitOfWork,
)
from foldmind_ai_core.adapters.outbound.postgres.outbox_repository import (
    PostgresOutboxRepository,
)
from foldmind_ai_core.adapters.outbound.postgres.projection_ledger_repository import (
    PostgresProjectionLedgerRepository,
)
from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
from foldmind_ai_core.adapters.outbound.postgres.task_repository import (
    PostgresTaskRepository,
)
from foldmind_ai_core.core.application.ports.outbound.vector_store import VectorWriteResult
from foldmind_ai_core.core.application.models.indexing import (
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.application.projections.vector import DocumentVectorProjection
from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.application.services.outbox_events import document_deleted_event
from foldmind_ai_core.core.domain.models.generation.results import (
    DocumentSearchItem,
    DocumentSearchResult,
    GeneratedTextResult,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentProfile,
    DocumentSignal,
    DocumentSignalType,
    SignalEvidence,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievedDocument
from foldmind_ai_core.core.domain.models.workflow.actions import (
    CreateFolderInput,
    HostAction,
    HostActionPolicy,
    HostActionStatus,
    HostActionType,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskCreationInput,
    TaskEvent,
    TaskEventType,
    TaskFinalResult,
    TaskJob,
    TaskJobResult,
    TaskJobStatus,
    TaskOutputType,
    TaskInputEntry,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.core.domain.services.profiling import (
    create_document_signal,
)

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


class FakeConnection:
    def __init__(
        self,
        rows: list[tuple[Any, ...]] | None = None,
        row_sets: list[list[tuple[Any, ...]]] | None = None,
    ) -> None:
        self.rows = rows or []
        self.row_sets = row_sets or []
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> FakeCursor:
        self.calls.append((sql, params))
        upper_sql = sql.lstrip().upper()
        returns_rows = upper_sql.startswith("SELECT") or "RETURNING" in upper_sql
        if (
            upper_sql.startswith("SELECT 1")
            and (
                "FROM DOCUMENT_SOURCES" in upper_sql
                or "FROM FOLDER_SOURCES" in upper_sql
            )
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

    def transaction(self) -> object:
        connection = self

        class Transaction:
            def __enter__(self) -> None:
                connection.pending_calls = []

            def __exit__(
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

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> FakeCursor:
        self.calls.append((sql, params))
        self.pending_calls.append((sql, params))
        if self.fail_on_outbox and "INSERT INTO outbox_events" in sql:
            raise RuntimeError("outbox insert failed")
        if self.fail_on_sql is not None and self.fail_on_sql in sql:
            raise RuntimeError("host action insert failed")
        upper_sql = sql.lstrip().upper()
        if (
            upper_sql.startswith("SELECT 1")
            and (
                "FROM DOCUMENT_SOURCES" in upper_sql
                or "FROM FOLDER_SOURCES" in upper_sql
            )
        ):
            return FakeCursor([(1,)])
        return FakeCursor([])


class PostgresAdapterTests(unittest.TestCase):
    def test_postgres_settings_reject_blank_dsn(self) -> None:
        with self.assertRaisesRegex(ValueError, "dsn"):
            PostgresSettings(dsn=" ")

        settings = PostgresSettings(dsn=" postgresql://not-used ")
        self.assertEqual(settings.dsn, "postgresql://not-used")

    def test_document_keyword_search_store_queries_sparse_chunk_projection(self) -> None:
        connection = FakeConnection(
            rows=[
                (
                    "tenant-1",
                    "document",
                    "doc-1",
                    "v1",
                    "index-input-v1",
                    "2026-05-01T10:00:00+09:00",
                    "2026-05-02T11:00:00+09:00",
                    "11111111-1111-4111-8111-111111111111",
                    0,
                    "A useful document.",
                    0,
                    18,
                    {"source": "test"},
                    0.75,
                )
            ]
        )

        results = PostgresDocumentKeywordSearchStore(
            client=_postgres_client(connection)
        ).search_chunks(
            tenant="tenant-1",
            query_text="useful document",
            top_k=5,
            scope=SearchScope(document_ids=("doc-1",), folder_ids=("folder-1",)),
        )

        sql = _all_sql(connection)
        self.assertIn("dc.search_vector @@ plainto_tsquery('simple', %s)", sql)
        self.assertIn("source_document_folder_relations", sql)
        self.assertEqual(results[0].chunk.text, "A useful document.")
        self.assertEqual(results[0].chunk.start_offset, 0)
        self.assertEqual(results[0].chunk.end_offset, 18)
        self.assertEqual(results[0].score, 0.75)
        self.assertEqual(
            connection.calls[0][1],
            (
                "useful document",
                "tenant-1",
                "useful document",
                ["doc-1"],
                ["folder-1"],
                5,
            ),
        )

    def test_index_repository_writes_normalized_document_index(self) -> None:
        connection = FakeConnection()
        repository = PostgresIndexRepository()

        repository.upsert_document_index_with_connection(
            connection,
            document=_sample_source_document(),
            chunks=(_sample_document_chunk(),),
            profile=_sample_document_profile(),
            signals=(_sample_document_signal(),),
        )

        self.assertIn("title", _all_sql(connection))
        self.assertIn("index_input_digest", _all_sql(connection))
        self.assertIn("generation_model", _all_sql(connection))
        self.assertIn("signal_generation_version", _all_sql(connection))
        self.assertIn("document_sources", _all_sql(connection))
        self.assertIn("ON CONFLICT (document_id)", _all_sql(connection))
        self.assertIn("source_created_at", _all_sql(connection))
        self.assertIn("source_updated_at", _all_sql(connection))
        self.assertIn("title = EXCLUDED.title", _all_sql(connection))
        self.assertIn(
            "WHERE document_sources.source_version <= EXCLUDED.source_version",
            _all_sql(connection),
        )
        self.assertIn("source_document_folder_relation", _all_sql(connection))
        self.assertNotIn("folder_ids = EXCLUDED.folder_ids", _all_sql(connection))
        self.assertNotIn("tag_ids", _all_sql(connection))
        self.assertIn("document_type = EXCLUDED.document_type", _all_sql(connection))
        self.assertNotIn("indexed_content_digest", _all_sql(connection))
        self.assertNotIn("title_digest", _all_sql(connection))
        self.assertNotIn("name_digest", _all_sql(connection))
        self.assertNotIn("path_digest", _all_sql(connection))
        self.assertNotIn("parent_folder_id_digest", _all_sql(connection))
        self.assertIn("ON CONFLICT (document_id)", _all_sql(connection))
        self.assertIn("ON CONFLICT (signal_id)", _all_sql(connection))
        self.assertNotIn("ON CONFLICT (tenant_id, signal_id)", _all_sql(connection))
        self.assertNotIn("latest_source_version", _all_sql(connection))
        self.assertNotIn("last_seen_at", _all_sql(connection))
        self.assertNotIn("document_index_records (\n    document_index_id,\n    tenant_id", _all_sql(connection))
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
            params
            for sql, params in connection.calls
            if "INSERT INTO document_chunks" in sql
        ]
        self.assertEqual(
            chunk_insert_params,
            [
                (
                    "11111111-1111-4111-8111-111111111111",
                    "tenant-1",
                    "doc-1",
                    "index-input-v1",
                    0,
                    "A useful document.",
                    0,
                    18,
                )
            ],
        )

    def test_index_repository_replaces_document_folder_relation(self) -> None:
        connection = FakeConnection(
            row_sets=[
                [(1,)],
                [("old-folder",)],
                [(1,)],
                [("folder-1",), ("folder-2",)],
            ]
        )

        updated = (
            PostgresIndexRepository()
            .replace_document_folder_relation_snapshot_with_connection(
                connection,
                snapshot=SourceDocumentFolderRelationSnapshot(
                    tenant="tenant-1",
                    document_id="doc-1",
                    source_version="v1",
                    folder_ids=("folder-1", "folder-2", "folder-1"),
                ),
            )
        )

        sql = _all_sql(connection)
        self.assertTrue(updated.applied)
        self.assertEqual(updated.previous_folder_ids, ("old-folder",))
        self.assertEqual(updated.current_folder_ids, ("folder-1", "folder-2"))
        self.assertIn("FROM document_sources", sql)
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
            relation_insert_params,
            [
                ("tenant-1", "doc-1", "folder-1"),
                ("tenant-1", "doc-1", "folder-2"),
            ],
        )

    def test_index_repository_represents_empty_folder_membership_as_no_rows(self) -> None:
        connection = FakeConnection(
            row_sets=[
                [(1,)],
                [("old-folder",)],
                [(1,)],
                [],
            ]
        )

        updated = (
            PostgresIndexRepository()
            .replace_document_folder_relation_snapshot_with_connection(
                connection,
                snapshot=SourceDocumentFolderRelationSnapshot(
                    tenant="tenant-1",
                    document_id="doc-1",
                    source_version="v2",
                    folder_ids=(),
                ),
            )
        )

        sql = _all_sql(connection)
        self.assertTrue(updated.applied)
        self.assertEqual(updated.previous_folder_ids, ("old-folder",))
        self.assertEqual(updated.current_folder_ids, ())
        self.assertIn("FROM document_sources", sql)
        self.assertNotIn("source_document_folder_relation_state", sql)
        self.assertIn("DELETE FROM source_document_folder_relations", sql)
        self.assertNotIn("INSERT INTO source_document_folder_relations", sql)

    def test_index_repository_ignores_stale_document_folder_relation(self) -> None:
        connection = FakeConnection(
            row_sets=[
                [(1,)],
                [("current-folder",)],
                [],
            ]
        )

        updated = (
            PostgresIndexRepository()
            .replace_document_folder_relation_snapshot_with_connection(
                connection,
                snapshot=_sample_folder_relation_snapshot(),
            )
        )

        sql = _all_sql(connection)
        self.assertFalse(updated.applied)
        self.assertEqual(updated.previous_folder_ids, ("current-folder",))
        self.assertEqual(updated.current_folder_ids, ("current-folder",))
        self.assertIn("FROM document_sources", sql)
        self.assertNotIn("source_document_folder_relation_state", sql)
        self.assertNotIn("DELETE FROM source_document_folder_relations", sql)
        self.assertNotIn("INSERT INTO source_document_folder_relations", sql)

    def test_index_repository_deletes_documents_by_global_document_id(
        self,
    ) -> None:
        connection = FakeConnection(
            row_sets=[
                [("tenant-1", "doc-1")],
                [("folder-1",), ("folder-2",)],
                [("tenant-1",)],
                [("folder-v1", "Folder 1", None, None, "", {})],
                [],
                [("tenant-1", "folder-1", "folder-signal-input-v1", "1")],
                [("tenant-1",)],
                [("folder-v1", "Folder 2", None, None, "", {})],
                [],
                [("tenant-1", "folder-2", "folder-signal-input-v1", "1")],
            ],
        )

        deleted = PostgresIndexRepository().mark_document_deleted_with_connection(
            connection,
            document_id="doc-1",
        )

        sql = _all_sql(connection)
        self.assertIsNotNone(deleted)
        self.assertEqual(deleted.tenant, "tenant-1")
        self.assertEqual(deleted.affected_folder_ids, ("folder-1", "folder-2"))
        self.assertNotIn("document_type = %s", sql)
        self.assertNotIn("IS NULL OR document_type", sql)
        self.assertIn("DELETE FROM folder_signals", sql)
        self.assertIn("folder_id = ANY", sql)
        self.assertIn("UPDATE folder_index_records", sql)
        self.assertIn("FROM source_document_folder_relations", sql)
        self.assertIn("DELETE FROM source_document_folder_relations", sql)
        self.assertNotIn("source_document_folder_relation_state", sql)
        self.assertNotIn("related_document_id = NULL", sql)
        params = [params for _, params in connection.calls]
        self.assertEqual(
            params[:3],
            [
                ("doc-1",),
                ("doc-1", "doc-1"),
                (["folder-1", "folder-2"],),
            ],
        )
        self.assertEqual(params[3][0], "folder-1")
        self.assertEqual(params[6][1], "folder-1")
        self.assertEqual(params[7][0], "folder-2")
        self.assertEqual(params[10][1], "folder-2")
        self.assertEqual(
            params[-5:],
            [
                ("doc-1",),
                ("doc-1",),
                ("doc-1",),
                ("doc-1",),
                ("tenant-1", "doc-1"),
            ],
        )

    def test_indexed_document_source_repository_reads_current_indexed_signals(
        self,
    ) -> None:
        connection = FakeConnection(
            row_sets=[
                [
                    (
                        "document",
                        "doc-1",
                        "v2",
                        "Indexed title",
                        "2026-05-18T10:00:00+09:00",
                        "2026-05-18T11:00:00+09:00",
                        {"source": "metadata"},
                    )
                ],
                [
                    ("signal-concept", "concept", "concept-b", "Concept text", 0.9),
                    ("signal-summary", "summary", "summary-a", "Summary text", 0.4),
                    ("signal-entity", "entity", "entity-a", "Entity text", None),
                ],
            ]
        )

        source = PostgresIndexedDocumentSourceRepository(
            client=_postgres_client(connection)
        ).get_current_document_source(tenant="tenant-1", document_id="doc-1")

        self.assertIsNotNone(source)
        self.assertEqual(source.tenant, "tenant-1")
        self.assertEqual(source.document_type, "document")
        self.assertEqual(source.document_id, "doc-1")
        self.assertEqual(source.source_version, "v2")
        self.assertEqual(source.title, "Indexed title")
        self.assertEqual(source.body, "Summary text\n\nConcept text\n\nEntity text")
        self.assertEqual(source.metadata, {"source": "metadata"})
        self.assertNotIn("is_current = true", _all_sql(connection))
        self.assertIn("document_sources.document_id = %s", _all_sql(connection))
        self.assertIn("document_index_records.deleted_at IS NULL", _all_sql(connection))
        self.assertNotIn("status = 'indexed'", _all_sql(connection))
        self.assertIn("FROM document_signals", _all_sql(connection))
        self.assertNotIn("scope_type = 'document'", _all_sql(connection))
        self.assertEqual(
            [params for _, params in connection.calls],
            [
                ("tenant-1", "doc-1"),
                ("doc-1",),
            ],
        )

    def test_indexed_document_source_repository_reads_current_folder_relations(
        self,
    ) -> None:
        connection = FakeConnection(row_sets=[[("folder-current",)]])

        folder_ids = PostgresIndexedDocumentSourceRepository(
            client=_postgres_client(connection)
        ).get_current_document_folder_ids(tenant="tenant-1", document_id="doc-1")

        self.assertEqual(folder_ids, ("folder-current",))
        self.assertIn(
            "FROM source_document_folder_relations",
            _all_sql(connection),
        )
        self.assertEqual([params for _, params in connection.calls], [("tenant-1", "doc-1")])

    def test_indexed_document_source_repository_returns_none_without_current_index(
        self,
    ) -> None:
        connection = FakeConnection(row_sets=[[]])

        source = PostgresIndexedDocumentSourceRepository(
            client=_postgres_client(connection)
        ).get_current_document_source(tenant="tenant-1", document_id="doc-1")

        self.assertIsNone(source)
        self.assertEqual([params for _, params in connection.calls], [("tenant-1", "doc-1")])

    def test_index_repository_writes_folder_ref_by_global_folder_id(self) -> None:
        connection = FakeConnection()

        PostgresIndexRepository().upsert_folder_index_with_connection(
            connection,
            folder=_sample_source_folder(),
        )

        sql = _all_sql(connection)
        self.assertIn("INSERT INTO folder_sources", sql)
        self.assertIn("ON CONFLICT (folder_id)", sql)
        self.assertIn("source_created_at", sql)
        self.assertIn("source_updated_at", sql)
        self.assertIn(
            "WHERE folder_sources.source_version <= EXCLUDED.source_version",
            sql,
        )
        self.assertNotIn("ON CONFLICT (tenant_id, folder_id)", sql)
        self.assertNotIn("name_digest", sql)
        self.assertNotIn("path_digest", sql)
        self.assertNotIn("parent_folder_id_digest", sql)

    def test_projection_ledger_records_vector_projection(
        self,
    ) -> None:
        connection = FakeConnection()
        repository = PostgresProjectionLedgerRepository(
            client=_postgres_client(connection),
        )

        repository.record_document_vector_projected(
            projection=DocumentVectorProjection(
                tenant="tenant-1",
                document_type="document",
                document_id="doc-1",
                source_version="v1",
                content_digest="content-digest-1",
                index_input_digest="index-input-v1",
                created_at="2026-05-01T10:00:00+09:00",
                updated_at="2026-05-02T11:00:00+09:00",
                embedding_input="Architecture memo",
                embedding_input_hash="hash-1",
                embedding_model="embedding",
                embedding_version="embedding-v1",
                index_schema_version="schema-v1",
            ),
            write=VectorWriteResult(
                collection_name="documents",
                point_id="11111111-1111-4111-8111-111111111111",
                payload_digest="digest-1",
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
            "ON CONFLICT (collection_name, point_id)",
            sql,
        )
        self.assertIn("source_kind = EXCLUDED.source_kind", sql)
        self.assertIn("vector_item_id = EXCLUDED.vector_item_id", sql)
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
            ("doc-1", "document", "doc-1", "index-input-v1"),
        )

    def test_projection_ledger_deletes_document_projections_by_document_id(
        self,
    ) -> None:
        connection = FakeConnection()
        repository = PostgresProjectionLedgerRepository(
            client=_postgres_client(connection),
        )

        repository.delete_document_vector_records(
            document_id="doc-1",
        )
        repository.delete_chunk_vector_records(
            document_id="doc-1",
        )
        repository.delete_signal_vector_records(
            document_id="doc-1",
        )
        repository.delete_folder_signal_vector_records(
            folder_id="folder-1",
        )

        self.assertEqual(
            [params for _, params in connection.calls],
            [
                ("document", "doc-1", ["document"]),
                ("document", "doc-1", ["chunk"]),
                ("document", "doc-1", ["signal"]),
                ("folder", "folder-1", ["signal"]),
            ],
        )
        self.assertIn("DELETE FROM vector_projection_records", _all_sql(connection))
        self.assertNotIn("SET deleted_at", _all_sql(connection))

    def test_outbox_repository_appends_event_with_debezium_key_fields(self) -> None:
        connection = FakeConnection()
        repository = PostgresOutboxRepository(client=_postgres_client(connection))
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
        )

        repository.append(event)

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
            getattr(params[7], "obj", None),
            {
                "tenant": "tenant-1",
                "document_id": "doc-1",
                "affected_folder_ids": [],
            },
        )
        self.assertEqual(event.partition_key, "document:tenant-1:doc-1")

    def test_indexing_unit_of_work_writes_profile_and_outbox_in_one_connection(self) -> None:
        connection = FakeConnection()
        profile = _sample_document_profile()
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
        )
        index_repository = PostgresIndexRepository()
        outbox_repository = PostgresOutboxRepository(client=_postgres_client(connection))
        uow = PostgresIndexingUnitOfWork(
            client=_postgres_client(connection),
            index_repository=index_repository,
            outbox_repository=outbox_repository,
        )

        with uow.transaction() as tx:
            tx.upsert_document_index(
                document=_sample_source_document(),
                chunks=(_sample_document_chunk(),),
                profile=profile,
                signals=(_sample_document_signal(),),
            )
            tx.append_outbox_event(event)

        sql = _all_sql(connection)
        self.assertIn("INSERT INTO document_sources", sql)
        self.assertNotIn("INSERT INTO source_document_snapshots", sql)
        self.assertIn("INSERT INTO document_index_records", sql)
        self.assertNotIn("INSERT INTO document_chunk_sets", sql)
        self.assertIn("INSERT INTO document_chunks", sql)
        self.assertIn("INSERT INTO document_signals", sql)
        self.assertIn("INSERT INTO outbox_events", sql)

    def test_indexing_unit_of_work_rolls_back_profile_when_outbox_insert_fails(
        self,
    ) -> None:
        connection = TransactionalFakeConnection(fail_on_outbox=True)
        profile = _sample_document_profile()
        event = document_deleted_event(
            tenant="tenant-1",
            document_id="doc-1",
        )
        index_repository = PostgresIndexRepository()
        outbox_repository = PostgresOutboxRepository(client=_postgres_client(connection))
        uow = PostgresIndexingUnitOfWork(
            client=_postgres_client(connection),
            index_repository=index_repository,
            outbox_repository=outbox_repository,
        )

        with self.assertRaisesRegex(RuntimeError, "outbox insert failed"):
            with uow.transaction() as tx:
                tx.upsert_document_index(
                    document=_sample_source_document(),
                    chunks=(_sample_document_chunk(),),
                    profile=profile,
                    signals=(_sample_document_signal(),),
                )
                tx.append_outbox_event(event)

        self.assertEqual(connection.rollback_count, 1)
        self.assertEqual(connection.committed_calls, [])
        self.assertIn("INSERT INTO document_index_records", _all_sql(connection))
        self.assertIn("INSERT INTO outbox_events", _all_sql(connection))

    def test_task_repository_rebuilds_snapshot_from_normalized_rows(self) -> None:
        request = TaskCreationInput(
            tenant="tenant-1",
            request="Draft a plan.",
            context=TaskContext(
                requested_at="2026-05-17T09:30:00+09:00",
                document_id="doc-context",
                folder_id="folder-context",
            ),
        )
        request_entry = TaskInputEntry(
            task_input_id=request.task_input_id,
            task_id=TASK_ID,
            input_text=request.request,
            context=request.context,
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
                DocumentSearchItem(
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
            tenant=request.tenant,
            request=request.request,
            context=request.context,
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
                [
                    (
                        snapshot.tenant,
                        snapshot.request,
                        {
                            "requested_at": snapshot.context.requested_at,
                            "document_id": snapshot.context.document_id,
                            "folder_id": snapshot.context.folder_id,
                        },
                        str(snapshot.status),
                        snapshot.analysis.message,
                        str(final_result.result_type),
                        domain_model_json(final_result.result),
                        final_result.title,
                        final_result.metadata,
                        snapshot.current_action_id,
                        {"message": snapshot.error} if snapshot.error else None,
                        snapshot.metadata,
                    )
                ],
                [
                    (
                        request_entry.task_input_id,
                        request_entry.input_text,
                        {
                            "requested_at": request_entry.context.requested_at,
                            "document_id": request_entry.context.document_id,
                            "folder_id": request_entry.context.folder_id,
                        },
                        request_entry.position,
                        str(request_entry.status),
                    )
                ],
                [
                    (
                        job.job_id,
                        job.round_index,
                        job.position,
                        job.job_type,
                        str(job.status),
                        job.reason,
                        job.input,
                        job.started_at,
                        job.finished_at,
                        None,
                        job.metadata,
                    ),
                ],
                [
                    (
                        OUTPUT_ID,
                        JOB_ID,
                        0,
                        str(TaskOutputType.SUMMARY),
                        domain_model_json(final_result.result),
                        {"text": "Done."},
                        {"visible": True},
                    ),
                    (
                        SEARCH_OUTPUT_ID,
                        JOB_ID,
                        1,
                        str(TaskOutputType.DOCUMENT_SEARCH_RESULT),
                        domain_model_json(search_result),
                        {"count": 1},
                        {},
                    )
                ],
                [
                    (
                        str(action.action_type),
                        action.summary,
                        domain_model_json(action.input),
                        action.action_id,
                        action.job_id,
                        action.reason,
                        str(action.status),
                        action.attempts,
                        domain_model_json(action.policy),
                        action.metadata,
                        0,
                    )
                ],
                [
                    (
                        event.event_id,
                        str(event.event_type),
                        event.message,
                        event.job_id,
                        event.data,
                    )
                ],
            ]
        )
        repository = PostgresTaskRepository(client=_postgres_client(connection))

        repository.create(snapshot)
        repository.save(snapshot)
        loaded = repository.get(task_id=TASK_ID)

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

    def test_task_repository_rejects_malformed_text_and_metadata_rows(self) -> None:
        malformed_current_action = FakeConnection(
            row_sets=[
                [
                    (
                        "tenant-1",
                        "Summarize this.",
                        {"requested_at": "2026-05-17T09:30:00+09:00"},
                        str(TaskStatus.CLARIFICATION_REQUIRED),
                        "Planning.",
                        None,
                        None,
                        None,
                        {},
                        123,
                        None,
                        {},
                    )
                ],
                [],
                [],
                [],
                [],
            ]
        )
        with self.assertRaisesRegex(ValueError, "current_action_id"):
            PostgresTaskRepository(
                client=_postgres_client(malformed_current_action)
            ).get(task_id=TASK_ID)

        malformed_metadata = FakeConnection(
            row_sets=[
                [
                    (
                        "tenant-1",
                        "Summarize this.",
                        {"requested_at": "2026-05-17T09:30:00+09:00"},
                        str(TaskStatus.CLARIFICATION_REQUIRED),
                        "Planning.",
                        None,
                        None,
                        None,
                        {},
                        None,
                        None,
                        [],
                    )
                ],
                [],
                [],
                [],
                [],
            ]
        )
        with self.assertRaisesRegex(ValueError, "metadata fields"):
            PostgresTaskRepository(client=_postgres_client(malformed_metadata)).get(
                task_id=TASK_ID
            )

    def test_task_repository_preserves_terminal_completion_time_until_reopened(self) -> None:
        connection = FakeConnection()
        repository = PostgresTaskRepository(client=_postgres_client(connection))
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Revise the plan.",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message="Task accepted for workflow planning."),
        )

        repository.save(snapshot)

        sql = _all_sql(connection)
        self.assertIn(
            "WHEN EXCLUDED.status IN ('completed', 'failed', 'rejected')",
            sql,
        )
        self.assertIn(
            "THEN COALESCE(tasks.completed_at, EXCLUDED.completed_at)",
            sql,
        )
        self.assertIn("ELSE NULL", sql)

    def test_task_repository_save_rolls_back_when_normalized_write_fails(self) -> None:
        connection = TransactionalFakeConnection(fail_on_sql="INSERT INTO host_actions")
        repository = PostgresTaskRepository(client=_postgres_client(connection))
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
            repository.save(snapshot)

        self.assertEqual(connection.rollback_count, 1)
        self.assertEqual(connection.committed_calls, [])
        self.assertIn("INSERT INTO tasks", _all_sql(connection))
        self.assertIn("INSERT INTO host_actions", _all_sql(connection))

def _all_sql(connection: FakeConnection) -> str:
    return "\n".join(sql for sql, _ in connection.calls)


def _postgres_client(connection: FakeConnection) -> PostgresClient:
    return PostgresClient(
        settings=PostgresSettings(dsn="postgresql://not-used"),
        connection=connection,
    )


def _sample_document_profile() -> DocumentProfile:
    return DocumentProfile(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        title="Architecture memo",
        index_input_digest="index-input-v1",
        metadata={"source": "test"},
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
        index_input_digest="index-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        chunk_id="11111111-1111-4111-8111-111111111111",
        chunk_index=0,
        chunking_version="chunking-v1",
        text="A useful document.",
        text_hash="hash-1",
        start_offset=0,
        end_offset=18,
        embedding_model="embedding",
        embedding_version="embedding-v1",
        index_schema_version="schema-v1",
    )


def _sample_document_signal() -> DocumentSignal:
    return create_document_signal(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        index_input_digest="index-input-v1",
        signal_type=DocumentSignalType.SUMMARY,
        text="A useful document.",
        attributes={},
        evidence=(SignalEvidence(chunk_id="chunk-1", quote="A useful document."),),
        confidence=0.9,
        extractor_name="test",
        extractor_version="v1",
        generation_model="model-a",
    )


if __name__ == "__main__":
    unittest.main()
