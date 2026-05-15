from __future__ import annotations

import unittest
from contextlib import contextmanager

from foldmind_ai_core.application.errors import (
    NoCandidatesError,
    ResourceNotFoundError,
)
from foldmind_ai_core.application.services.document_chunker import (
    DocumentChunker,
    DocumentChunkingConfig,
)
from foldmind_ai_core.application.services.workflow_request_queue import (
    WorkflowRequestQueue,
)
from foldmind_ai_core.application.use_cases.indexing.delete_document_index import (
    DeleteDocumentIndexUseCase,
)
from foldmind_ai_core.application.use_cases.indexing.index_document import IndexDocumentUseCase
from foldmind_ai_core.application.use_cases.recommendation.recommend_folder import (
    RecommendFolderUseCase,
)
from foldmind_ai_core.application.use_cases.workflow.get_task import GetTaskUseCase
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.indexing.outbox import OutboxEvent
from foldmind_ai_core.domain.profiling.concepts import profile_concepts_from_labels
from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.workflow.tasks import (
    TaskAppendRequest,
    TaskCreationRequest,
    TaskRequestStatus,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.validation import InvalidInputError

TEST_CHUNKING_VERSION = "chunking-test-v1"
TEST_EMBEDDING_MODEL = "embedding-test-model"
TEST_EMBEDDING_VERSION = "embedding-test-v1"
TEST_INDEX_SCHEMA_VERSION = "index-schema-test-v1"


class FakeIndexingTransaction:
    def __init__(self) -> None:
        self.document_profiles: list[DocumentProfile] = []
        self.deleted_documents: list[str] = []
        self.events: list[OutboxEvent] = []
        self.operations: list[str] = []

    def upsert_document_profile(self, profile: DocumentProfile) -> None:
        self.document_profiles.append(profile)
        self.operations.append("upsert_profile")

    def delete_document_profile(self, *, document_id: str) -> None:
        self.deleted_documents.append(document_id)
        self.operations.append("delete_profile")

    def append_outbox_event(self, event: OutboxEvent) -> None:
        self.events.append(event)
        self.operations.append("append_outbox")


class FakeIndexingUnitOfWork:
    def __init__(self) -> None:
        self.tx = FakeIndexingTransaction()
        self.opened = 0

    @contextmanager
    def transaction(self):
        self.opened += 1
        yield self.tx


class FakeDocumentProfiler:
    def profile(
        self,
        document: SourceDocument,
        chunks: list[DocumentChunk],
    ) -> DocumentProfile:
        return DocumentProfile(
            tenant=document.tenant,
            document_type=document.document_type,
            document_id=document.document_id,
            source_version=document.source_version,
            title=document.title or document.document_id,
            profile_version="profile-v1",
            profile_schema_version="1",
            summary="Document summary",
            concepts=profile_concepts_from_labels(
                tenant=document.tenant,
                labels=("Document summary",),
            ),
        )


class FakeTaskRepository:
    def get(self, *, task_id: str) -> TaskSnapshot | None:
        return None

    def get_by_request_id(self, *, task_request_id: str) -> TaskSnapshot | None:
        return None

    def get_by_action_id(self, *, action_id: str) -> TaskSnapshot | None:
        return None

    def create(self, snapshot: TaskSnapshot) -> None:
        return None

    def save(self, snapshot: TaskSnapshot) -> None:
        return None


class EmptyFolderFinder:
    def execute(self, request: SourceDocument):
        return []


def make_document(*, body: str = "body") -> SourceDocument:
    return SourceDocument(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        title="",
        body=body,
    )


def make_index_document_use_case(
    *,
    uow: FakeIndexingUnitOfWork | None = None,
    chunk_size: int = 1200,
    chunk_overlap: int = 120,
) -> IndexDocumentUseCase:
    return IndexDocumentUseCase(
        profiler=FakeDocumentProfiler(),
        indexing_uow=uow or FakeIndexingUnitOfWork(),
        chunker=DocumentChunker(
            DocumentChunkingConfig(
                chunking_version=TEST_CHUNKING_VERSION,
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        ),
    )


class UseCaseRefactoringTests(unittest.TestCase):
    def test_empty_document_indexing_deletes_profile_and_publishes_outbox_event(self) -> None:
        uow = FakeIndexingUnitOfWork()

        result = make_index_document_use_case(
            uow=uow,
        ).execute(make_document(body=" "))

        self.assertEqual(result, [])
        self.assertEqual(uow.tx.deleted_documents, ["doc-1"])
        self.assertEqual([event.event_type for event in uow.tx.events], ["DOCUMENT_DELETED"])
        self.assertEqual(uow.tx.events[0].aggregate_id, "doc-1")
        self.assertEqual(uow.tx.operations, ["delete_profile", "append_outbox"])

    def test_explicit_document_delete_deletes_profile_and_publishes_outbox_event(self) -> None:
        uow = FakeIndexingUnitOfWork()

        DeleteDocumentIndexUseCase(
            indexing_uow=uow,
        ).execute(document_id="doc-1")

        self.assertEqual(uow.tx.deleted_documents, ["doc-1"])
        self.assertEqual([event.event_type for event in uow.tx.events], ["DOCUMENT_DELETED"])
        self.assertEqual(
            f"{uow.tx.events[0].aggregate_type}:{uow.tx.events[0].aggregate_id}",
            "DOCUMENT:doc-1",
        )

    def test_document_indexing_writes_profile_and_event_in_same_transaction(self) -> None:
        uow = FakeIndexingUnitOfWork()

        chunks = make_index_document_use_case(
            uow=uow,
        ).execute(make_document())

        self.assertEqual(len(chunks), 1)
        self.assertEqual(len(uow.tx.document_profiles), 1)
        self.assertEqual([event.event_type for event in uow.tx.events], ["DOCUMENT_INDEXED"])
        self.assertEqual(uow.tx.events[0].payload["chunks"][0]["text"], "body")
        self.assertEqual(uow.tx.operations, ["upsert_profile", "append_outbox"])

    def test_document_chunker_validates_config_and_preserves_offsets(self) -> None:
        chunks = DocumentChunker(
            DocumentChunkingConfig(
                chunking_version=TEST_CHUNKING_VERSION,
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
                chunk_size=4,
                chunk_overlap=1,
            )
        ).chunk(make_document(body="abcdefg"))

        self.assertEqual([chunk.text for chunk in chunks], ["abcd", "defg", "g"])
        self.assertTrue(all(chunk.text_hash for chunk in chunks))
        self.assertEqual(chunks[0].embedding_model, TEST_EMBEDDING_MODEL)
        self.assertEqual(chunks[0].embedding_version, TEST_EMBEDDING_VERSION)
        self.assertEqual(chunks[0].index_schema_version, TEST_INDEX_SCHEMA_VERSION)
        self.assertEqual(
            [(chunk.start_offset, chunk.end_offset) for chunk in chunks],
            [(0, 4), (3, 7), (6, 7)],
        )
        with self.assertRaises(InvalidInputError):
            DocumentChunkingConfig(
                chunking_version=TEST_CHUNKING_VERSION,
                embedding_model=TEST_EMBEDDING_MODEL,
                embedding_version=TEST_EMBEDDING_VERSION,
                index_schema_version=TEST_INDEX_SCHEMA_VERSION,
                chunk_size=4,
                chunk_overlap=4,
            )

    def test_use_cases_raise_explicit_expected_errors(self) -> None:
        with self.assertRaises(NoCandidatesError):
            RecommendFolderUseCase(find_folders=EmptyFolderFinder()).execute(make_document())
        with self.assertRaises(ResourceNotFoundError):
            GetTaskUseCase(task_repository=FakeTaskRepository()).execute(
                task_id="55555555-5555-4555-8555-555555555555",
            )

    def test_workflow_request_queue_owns_request_state_transitions(self) -> None:
        queue = WorkflowRequestQueue()
        snapshot = queue.initial_snapshot(
            TaskCreationRequest(
                tenant="tenant-1",
                request="First request",
                task_request_id="request-1",
            ),
            task_id="task-1",
        )
        snapshot.status = TaskStatus.READY_FOR_HOST_ACTION
        snapshot.current_action_id = "action-1"
        snapshot.error = "old error"

        queue.append_request(
            snapshot,
            TaskAppendRequest(
                request="Second request",
                task_id="task-1",
                task_request_id="request-2",
            ),
        )
        should_replan = queue.remove_request(snapshot, "request-1")

        self.assertTrue(should_replan)
        self.assertEqual(snapshot.request, "Second request")
        self.assertEqual(snapshot.status, TaskStatus.CLARIFICATION_REQUIRED)
        self.assertIsNone(snapshot.current_action_id)
        self.assertIsNone(snapshot.error)
        self.assertEqual(snapshot.requests[0].status, TaskRequestStatus.REMOVED)
        self.assertEqual(snapshot.analysis.message, "Task request removed. Task replanned.")

        snapshot.host_actions = [object()]  # type: ignore[list-item]
        should_replan = queue.remove_request(snapshot, "request-2")

        self.assertFalse(should_replan)
        self.assertEqual(snapshot.request, "")
        self.assertEqual(snapshot.host_actions, [])
        self.assertEqual(snapshot.analysis.message, "Task has no active requests.")


if __name__ == "__main__":
    unittest.main()
