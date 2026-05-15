from __future__ import annotations

import unittest
from typing import Any

from foldmind_ai_core.adapters.outbound.model_codec import model_value
from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
from foldmind_ai_core.adapters.outbound.postgres.indexing_unit_of_work import (
    PostgresIndexingUnitOfWork,
)
from foldmind_ai_core.adapters.outbound.postgres.outbox_repository import (
    PostgresOutboxRepository,
)
from foldmind_ai_core.adapters.outbound.postgres.profile_repository import (
    PostgresProfileRepository,
)
from foldmind_ai_core.adapters.outbound.postgres.settings import PostgresSettings
from foldmind_ai_core.adapters.outbound.postgres.task_repository import (
    PostgresTaskRepository,
)
from foldmind_ai_core.application.services.outbox_events import document_deleted_event
from foldmind_ai_core.domain.common import Confidence
from foldmind_ai_core.domain.generation.results import GeneratedTextResult
from foldmind_ai_core.domain.profiling.concepts import profile_concepts_from_labels
from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.domain.workflow.actions import (
    CreateFolderInput,
    HostAction,
    HostActionPolicy,
    HostActionStatus,
)
from foldmind_ai_core.domain.workflow.tasks import (
    TaskAnalysis,
    TaskCreationRequest,
    TaskEvent,
    TaskEventType,
    TaskOutput,
    TaskOutputType,
    TaskRequestEntry,
    TaskSnapshot,
    TaskStatus,
)

TASK_ID = "55555555-5555-4555-8555-555555555555"
ACTION_ID = "66666666-6666-4666-8666-666666666666"
DEPENDENCY_ACTION_ID = "77777777-7777-4777-8777-777777777777"
OUTPUT_ID = "88888888-8888-4888-8888-888888888888"
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
        rows = self.row_sets.pop(0) if returns_rows and self.row_sets else self.rows
        return FakeCursor(rows)


class TransactionalFakeConnection(FakeConnection):
    def __init__(self, *, fail_on_outbox: bool = False) -> None:
        super().__init__()
        self.fail_on_outbox = fail_on_outbox
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
        return FakeCursor([])


class PostgresAdapterTests(unittest.TestCase):
    def test_profile_repository_round_trips_normalized_document_profile(self) -> None:
        profile = DocumentProfile(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            title="Architecture memo",
            summary="A useful document.",
            profile_version="profile-v1",
            profile_schema_version="1",
            concepts=profile_concepts_from_labels(
                tenant="tenant-1",
                labels=("architecture", "derived index", "postgres"),
                confidence=Confidence(0.9),
            ),
            profile_confidence=0.9,
            model="model-a",
            prompt_version="prompt-v1",
            metadata={"source": "test"},
        )
        connection = FakeConnection(
            row_sets=[
                *_document_profile_row_sets(profile),
                *_document_profile_row_sets(profile),
            ]
        )
        repository = PostgresProfileRepository(client=_postgres_client(connection))

        repository.upsert(profile)
        loaded = repository.get_document_profile(
            document_id="doc-1",
        )

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded, profile)
        self.assertIn("title", _all_sql(connection))
        self.assertIn("concepts_json", _all_sql(connection))
        self.assertNotIn("topics", _all_sql(connection))
        self.assertNotIn("suggested_tags", _all_sql(connection))
        self.assertNotIn("document_profile_terms", _all_sql(connection))
        self.assertNotIn("document_profile_folder_suggestions", _all_sql(connection))
        self.assertNotIn("document_profile_items", _all_sql(connection))
        self.assertNotIn("document_profile_evidence_spans", _all_sql(connection))
        self.assertNotIn("document_profile_chunk_mentions", _all_sql(connection))
        self.assertNotIn("folder_documents_ref", _all_sql(connection))
        self.assertNotIn("profile_json", _all_sql(connection))

    def test_outbox_repository_appends_event_with_debezium_key_fields(self) -> None:
        connection = FakeConnection()
        repository = PostgresOutboxRepository(client=_postgres_client(connection))
        event = document_deleted_event(
            document_id="doc-1",
        )

        repository.append(event)

        self.assertEqual(len(connection.calls), 1)
        sql, params = connection.calls[0]
        self.assertIn("outbox_events", sql)
        self.assertEqual(params[1], "DOCUMENT")
        self.assertEqual(params[2], "doc-1")
        self.assertEqual(params[3], "DOCUMENT:doc-1")
        self.assertEqual(params[4], "DOCUMENT_DELETED")
        self.assertEqual(params[5], "1")
        self.assertEqual(getattr(params[6], "obj", None), {"document_id": "doc-1"})
        self.assertEqual(event.event_key, "DOCUMENT:doc-1")

    def test_outbox_repository_reads_latest_aggregate_sequence(self) -> None:
        connection = FakeConnection(rows=[(42,)])
        repository = PostgresOutboxRepository(client=_postgres_client(connection))

        sequence = repository.latest_sequence_for(
            aggregate_type="DOCUMENT",
            aggregate_id="doc-1",
        )

        self.assertEqual(sequence, 42)
        sql, params = connection.calls[0]
        self.assertIn("ORDER BY sequence DESC", sql)
        self.assertEqual(params, ("DOCUMENT", "doc-1"))

    def test_indexing_unit_of_work_writes_profile_and_outbox_in_one_connection(self) -> None:
        connection = FakeConnection()
        profile = _sample_document_profile()
        event = document_deleted_event(
            document_id="doc-1",
        )
        profile_repository = PostgresProfileRepository(client=_postgres_client(connection))
        outbox_repository = PostgresOutboxRepository(client=_postgres_client(connection))
        uow = PostgresIndexingUnitOfWork(
            client=_postgres_client(connection),
            profile_repository=profile_repository,
            outbox_repository=outbox_repository,
        )

        with uow.transaction() as tx:
            tx.upsert_document_profile(profile)
            tx.append_outbox_event(event)

        sql = _all_sql(connection)
        self.assertIn("INSERT INTO document_profiles", sql)
        self.assertIn("INSERT INTO outbox_events", sql)

    def test_indexing_unit_of_work_rolls_back_profile_when_outbox_insert_fails(
        self,
    ) -> None:
        connection = TransactionalFakeConnection(fail_on_outbox=True)
        profile = _sample_document_profile()
        event = document_deleted_event(
            document_id="doc-1",
        )
        profile_repository = PostgresProfileRepository(client=_postgres_client(connection))
        outbox_repository = PostgresOutboxRepository(client=_postgres_client(connection))
        uow = PostgresIndexingUnitOfWork(
            client=_postgres_client(connection),
            profile_repository=profile_repository,
            outbox_repository=outbox_repository,
        )

        with self.assertRaisesRegex(RuntimeError, "outbox insert failed"):
            with uow.transaction() as tx:
                tx.upsert_document_profile(profile)
                tx.append_outbox_event(event)

        self.assertEqual(connection.rollback_count, 1)
        self.assertEqual(connection.committed_calls, [])
        self.assertIn("INSERT INTO document_profiles", _all_sql(connection))
        self.assertIn("INSERT INTO outbox_events", _all_sql(connection))

    def test_task_repository_rebuilds_snapshot_from_normalized_rows(self) -> None:
        request = TaskCreationRequest(
            tenant="tenant-1",
            request="Draft a plan.",
        )
        request_entry = TaskRequestEntry(
            task_request_id=request.task_request_id,
            task_id=TASK_ID,
            request=request.request,
            position=0,
        )
        output = TaskOutput(
            output_type=TaskOutputType.SUMMARY,
            result=GeneratedTextResult(text="Done."),
            output_id=OUTPUT_ID,
            title="Summary",
            metadata={"visible": True},
        )
        action = HostAction(
            action_type="create_folder",
            summary="Create folder",
            input=CreateFolderInput(name="Plans"),
            action_id=ACTION_ID,
            reason="Needed for organization.",
            status=HostActionStatus.READY,
            attempts=1,
            depends_on=[DEPENDENCY_ACTION_ID],
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
            data={"ok": True},
        )
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant=request.tenant,
            request=request.request,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done.", outputs=[output]),
            requests=[request_entry],
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
                        str(snapshot.status),
                        snapshot.analysis.message,
                        snapshot.current_action_id,
                        {"message": snapshot.error} if snapshot.error else None,
                        snapshot.metadata,
                    )
                ],
                [
                    (
                        request_entry.task_request_id,
                        request_entry.request,
                        request_entry.position,
                        str(request_entry.status),
                    )
                ],
                [
                    (
                        str(output.output_type),
                        model_value(output.result),
                        output.output_id,
                        output.title,
                        output.metadata,
                    )
                ],
                [
                    (
                        str(action.action_type),
                        action.summary,
                        model_value(action.input),
                        action.action_id,
                        action.reason,
                        str(action.status),
                        action.attempts,
                        model_value(action.policy),
                        action.metadata,
                        0,
                    )
                ],
                [(ACTION_ID, DEPENDENCY_ACTION_ID)],
                [
                    (
                        event.event_id,
                        str(event.event_type),
                        event.message,
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
        self.assertIn("task_outputs", _all_sql(connection))
        self.assertIn("host_actions", _all_sql(connection))
        self.assertIn("data_json", _all_sql(connection))
        self.assertNotIn("snapshot_json", _all_sql(connection))
        self.assertNotIn("event_json", _all_sql(connection))


def _document_profile_row_sets(profile: DocumentProfile) -> list[list[tuple[Any, ...]]]:
    return [
        [
            (
                profile.tenant,
                profile.document_type,
                profile.document_id,
                profile.source_version,
                profile.profile_version,
                profile.profile_schema_version,
                profile.title,
                profile.summary,
                [
                    {
                        "concept_id": concept.concept_id,
                        "concept_key": concept.concept_key,
                        "label": concept.label,
                        "confidence": concept.confidence,
                        "evidence_chunk_ids": list(concept.evidence_chunk_ids),
                        "metadata": concept.metadata,
                    }
                    for concept in profile.concepts
                ],
                profile.profile_confidence,
                profile.model,
                profile.prompt_version,
                profile.metadata,
            )
        ],
    ]


def _all_sql(connection: FakeConnection) -> str:
    return "\n".join(sql for sql, _ in connection.calls)


def _postgres_client(connection: FakeConnection) -> PostgresClient:
    return PostgresClient(
        settings=PostgresSettings(dsn="postgresql://unused"),
        connection=connection,
    )


def _sample_document_profile() -> DocumentProfile:
    return DocumentProfile(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        title="Architecture memo",
        summary="A useful document.",
        profile_version="profile-v1",
        profile_schema_version="1",
        concepts=profile_concepts_from_labels(
            tenant="tenant-1",
            labels=("architecture", "derived index", "postgres"),
            confidence=Confidence(0.9),
        ),
        profile_confidence=0.9,
        model="model-a",
        prompt_version="prompt-v1",
        metadata={"source": "test"},
    )


if __name__ == "__main__":
    unittest.main()
