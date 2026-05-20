from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from foldmind_ai_core.adapters.inbound.http.routers.indexing import create_indexing_router
from foldmind_ai_core.adapters.inbound.http.routers.tasks import create_tasks_router
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.commands.indexing import (
    DeleteDocumentIndexCommand,
    DeleteFolderIndexCommand,
    IndexDocumentCommand,
    IndexFolderCommand,
    UpdateDocumentFolderRelationsCommand,
)
from foldmind_ai_core.core.application.commands.workflow import (
    AppendTaskInputCommand,
    CreateTaskCommand,
    GetTaskQuery,
    HostActionResultCommand,
    RecordActionResultCommand,
    RemoveTaskInputCommand,
)
from foldmind_ai_core.core.application.factories.workflow_commands import (
    task_context_from_command,
)
from foldmind_ai_core.core.application.factories.workflow_results import (
    record_action_result_from_snapshot,
    task_result_from_snapshot,
)
from foldmind_ai_core.core.application.results.indexing import (
    IndexDocumentResult,
    IndexFolderResult,
)
from foldmind_ai_core.core.application.results.retrieval import (
    RetrievedChunkResult,
)
from foldmind_ai_core.core.application.results.workflow import (
    RecordActionResult,
    TaskResult,
)
from foldmind_ai_core.bootstrap.api_use_cases import APIUseCases
from foldmind_ai_core.bootstrap.app_factory import create_app
from foldmind_ai_core.bootstrap.settings import APISettings
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.application.queries.retrieval import (
    RetrievalQuery,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskInputEntry,
    TaskSnapshot,
    TaskStatus,
)

DOCUMENT_ID = "11111111-1111-4111-8111-111111111111"
FOLDER_ID = "22222222-2222-4222-8222-222222222222"
TASK_ID = "55555555-5555-4555-8555-555555555555"
ACTION_ID = "66666666-6666-4666-8666-666666666666"
ACTION_ID_2 = "77777777-7777-4777-8777-777777777777"
ACTION_ID_3 = "88888888-8888-4888-8888-888888888888"
SOURCE_CREATED_AT = "2026-05-01T10:00:00+09:00"
SOURCE_UPDATED_AT = "2026-05-02T11:00:00+09:00"
REQUESTED_AT = "2026-05-17T09:30:00+09:00"


def make_chunk(chunk_id: str = "doc-1:chunk:0", text: str = "meeting notes") -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        chunk_id=chunk_id,
        chunk_index=0,
        chunking_version="chunking-test-v1",
        text=text,
        text_hash="hash-1",
        start_offset=0,
        end_offset=len(text),
        embedding_model="test-embedding",
        embedding_version="test-v1",
        index_schema_version="schema-v1",
    )


def make_retrieved_chunk_result(
    chunk_id: str = "doc-1:chunk:0",
    text: str = "meeting notes",
    score: float = 0.75,
) -> RetrievedChunkResult:
    chunk = make_chunk(chunk_id=chunk_id, text=text)
    return RetrievedChunkResult(
        tenant=chunk.tenant,
        document_type=chunk.document_type,
        document_id=chunk.document_id,
        source_version=chunk.source_version,
        created_at=chunk.created_at,
        updated_at=chunk.updated_at,
        chunk_id=chunk.chunk_id,
        chunk_index=chunk.chunk_index,
        chunking_version=chunk.chunking_version,
        text=chunk.text,
        text_hash=chunk.text_hash,
        start_offset=chunk.start_offset,
        end_offset=chunk.end_offset,
        embedding_model=chunk.embedding_model,
        embedding_version=chunk.embedding_version,
        index_schema_version=chunk.index_schema_version,
        score=score,
        metadata=dict(chunk.metadata),
    )


class FakeIndexDocumentUseCase:
    def __init__(self) -> None:
        self.command: IndexDocumentCommand | None = None

    def execute(self, command: IndexDocumentCommand) -> IndexDocumentResult:
        self.command = command
        return IndexDocumentResult(indexed_chunk_count=1)


class FakeDeleteDocumentIndexUseCase:
    def __init__(self) -> None:
        self.deleted: DeleteDocumentIndexCommand | None = None

    def execute(self, command: DeleteDocumentIndexCommand) -> None:
        self.deleted = command


class FakeUpdateDocumentFolderRelationsUseCase:
    def __init__(self) -> None:
        self.command: UpdateDocumentFolderRelationsCommand | None = None

    def execute(self, command: UpdateDocumentFolderRelationsCommand) -> None:
        self.command = command


class FakeIndexFolderUseCase:
    def __init__(self) -> None:
        self.command: IndexFolderCommand | None = None

    def execute(self, command: IndexFolderCommand) -> IndexFolderResult:
        self.command = command
        return IndexFolderResult(
            tenant=command.tenant,
            folder_id=command.folder_id,
            source_version=command.source_version,
        )


class FakeDeleteFolderIndexUseCase:
    def __init__(self) -> None:
        self.deleted: DeleteFolderIndexCommand | None = None

    def execute(self, command: DeleteFolderIndexCommand) -> None:
        self.deleted = command


class FakeRunTaskUseCase:
    def __init__(self) -> None:
        self.command: CreateTaskCommand | AppendTaskInputCommand | None = None
        self.missing_task_ids: set[str] = set()

    def execute(self, command: CreateTaskCommand | AppendTaskInputCommand) -> TaskResult:
        self.command = command
        if isinstance(command, AppendTaskInputCommand) and command.task_id in self.missing_task_ids:
            raise ResourceNotFoundError(f"Task not found: {command.task_id}")
        task_id = command.task_id if isinstance(command, AppendTaskInputCommand) else TASK_ID
        tenant = command.tenant if isinstance(command, CreateTaskCommand) else "tenant-1"
        context = task_context_from_command(command.context)
        return task_result_from_snapshot(
            TaskSnapshot(
                task_id=task_id,
                tenant=tenant,
                request=command.request,
                context=context,
                status=TaskStatus.CLARIFICATION_REQUIRED,
                analysis=TaskAnalysis(message="Task accepted."),
                inputs=[
                    TaskInputEntry(
                        task_input_id="99999999-9999-4999-8999-000000000000",
                        task_id=task_id,
                        input_text=command.request,
                        context=context,
                        position=0,
                    )
                ],
            )
        )


class FakeGetTaskUseCase:
    def __init__(self) -> None:
        self.snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Summarize the document",
            context=TaskContext(requested_at=REQUESTED_AT),
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message="Task accepted."),
        )

    def execute(self, query: GetTaskQuery) -> TaskResult:
        if query.task_id != self.snapshot.task_id:
            raise ResourceNotFoundError(f"Task not found: {query.task_id}")
        return task_result_from_snapshot(self.snapshot)


class FakeRecordActionResultUseCase:
    def __init__(self) -> None:
        self.recorded: HostActionResultCommand | None = None

    def execute(self, command: RecordActionResultCommand) -> RecordActionResult:
        self.recorded = command.result
        return record_action_result_from_snapshot(
            recorded=True,
            snapshot=TaskSnapshot(
                task_id=TASK_ID,
                tenant="tenant-1",
                request="Summarize the document",
                context=TaskContext(requested_at=REQUESTED_AT),
                status=TaskStatus.COMPLETED,
                analysis=TaskAnalysis(message="Task completed."),
                current_action_id=command.result.action_id,
            ),
        )


class FakeRemoveTaskInputUseCase:
    def __init__(self) -> None:
        self.removed: RemoveTaskInputCommand | None = None

    def execute(self, command: RemoveTaskInputCommand) -> TaskResult:
        self.removed = command
        return task_result_from_snapshot(
            TaskSnapshot(
                task_id=TASK_ID,
                tenant="tenant-1",
                request="",
                context=TaskContext(requested_at=REQUESTED_AT),
                status=TaskStatus.CLARIFICATION_REQUIRED,
                analysis=TaskAnalysis(message="Task has no active inputs."),
                inputs=[
                    TaskInputEntry(
                        task_input_id=command.task_input_id,
                        task_id=TASK_ID,
                        input_text="Summarize the document",
                        context=TaskContext(requested_at=REQUESTED_AT),
                        position=0,
                    )
                ],
            )
        )


class ApiRouteTests(unittest.TestCase):
    def test_create_app_registers_routes(self) -> None:
        use_cases = APIUseCases(
            index_document=FakeIndexDocumentUseCase(),
            delete_document_index=FakeDeleteDocumentIndexUseCase(),
            update_document_folder_relations=FakeUpdateDocumentFolderRelationsUseCase(),
            index_folder=FakeIndexFolderUseCase(),
            delete_folder_index=FakeDeleteFolderIndexUseCase(),
            run_task=FakeRunTaskUseCase(),
            get_task=FakeGetTaskUseCase(),
            remove_task_input=FakeRemoveTaskInputUseCase(),
            record_action_result=FakeRecordActionResultUseCase(),
        )
        app = create_app(
            use_cases,
            settings=APISettings(cors_origins=("http://localhost:3000",)),
        )
        client = TestClient(app)

        health_response = client.get("/health")
        search_response = client.post(
            "/retrieval/search",
            json={
                "query": {
                    "text": "Find the last meeting notes",
                    "request_context": {"tenant": "tenant-1"},
                }
            },
        )

        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json(), {"status": "ok"})
        self.assertEqual(search_response.status_code, 404)

    def test_indexing_routes_call_use_cases(self) -> None:
        index_document = FakeIndexDocumentUseCase()
        delete_document_index = FakeDeleteDocumentIndexUseCase()
        update_document_folder_relations = FakeUpdateDocumentFolderRelationsUseCase()
        index_folder = FakeIndexFolderUseCase()
        delete_folder_index = FakeDeleteFolderIndexUseCase()
        app = FastAPI()
        app.include_router(
            create_indexing_router(
                index_document=index_document,
                delete_document_index=delete_document_index,
                update_document_folder_relations=update_document_folder_relations,
                index_folder=index_folder,
                delete_folder_index=delete_folder_index,
            )
        )
        client = TestClient(app)

        index_response = client.post(
            "/indexing/documents",
            json={
                "document": {
                    "tenant": "tenant-1",
                    "document_type": "document",
                    "document_id": DOCUMENT_ID,
                    "source_version": "v1",
                    "created_at": SOURCE_CREATED_AT,
                    "updated_at": SOURCE_UPDATED_AT,
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                }
            },
        )

        self.assertEqual(index_response.status_code, 200)
        self.assertEqual(index_response.json(), {"indexed_chunk_count": 1})
        self.assertIsNotNone(index_document.command)
        self.assertEqual(index_document.command.document_id, DOCUMENT_ID)
        self.assertEqual(index_document.command.created_at, SOURCE_CREATED_AT)
        self.assertEqual(index_document.command.updated_at, SOURCE_UPDATED_AT)

        document_with_relation_response = client.post(
            "/indexing/documents",
            json={
                "document": {
                    "tenant": "tenant-1",
                    "document_type": "document",
                    "document_id": DOCUMENT_ID,
                    "source_version": "v1",
                    "created_at": SOURCE_CREATED_AT,
                    "updated_at": SOURCE_UPDATED_AT,
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                    "folder_relation_snapshot": {
                        "source_version": "v1",
                        "folder_ids": [FOLDER_ID],
                    },
                }
            },
        )

        self.assertEqual(document_with_relation_response.status_code, 422)

        index_without_type_response = client.post(
            "/indexing/documents",
            json={
                "document": {
                    "tenant": "tenant-1",
                    "document_id": DOCUMENT_ID,
                    "source_version": "v1",
                    "created_at": SOURCE_CREATED_AT,
                    "updated_at": SOURCE_UPDATED_AT,
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                }
            },
        )

        self.assertEqual(index_without_type_response.status_code, 200)
        self.assertIsNotNone(index_document.command)
        self.assertIsNone(index_document.command.document_type)

        missing_document_timestamp_response = client.post(
            "/indexing/documents",
            json={
                "document": {
                    "tenant": "tenant-1",
                    "document_type": "document",
                    "document_id": DOCUMENT_ID,
                    "source_version": "v1",
                    "updated_at": SOURCE_UPDATED_AT,
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                }
            },
        )

        self.assertEqual(missing_document_timestamp_response.status_code, 422)

        naive_document_timestamp_response = client.post(
            "/indexing/documents",
            json={
                "document": {
                    "tenant": "tenant-1",
                    "document_type": "document",
                    "document_id": DOCUMENT_ID,
                    "source_version": "v1",
                    "created_at": "2026-05-01T10:00:00",
                    "updated_at": SOURCE_UPDATED_AT,
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                }
            },
        )

        self.assertEqual(naive_document_timestamp_response.status_code, 422)

        normalized_index_response = client.post(
            "/indexing/documents",
            json={
                "document": {
                    "tenant": " tenant-1 ",
                    "document_type": " document ",
                    "document_id": f" {DOCUMENT_ID} ",
                    "source_version": " v1 ",
                    "created_at": f" {SOURCE_CREATED_AT} ",
                    "updated_at": f" {SOURCE_UPDATED_AT} ",
                    "title": " Meeting notes ",
                    "body": " Prepare next meeting ",
                }
            },
        )

        self.assertEqual(normalized_index_response.status_code, 200)
        self.assertIsNotNone(index_document.command)
        self.assertEqual(index_document.command.tenant, "tenant-1")
        self.assertEqual(index_document.command.document_type, "document")
        self.assertEqual(index_document.command.document_id, DOCUMENT_ID)
        self.assertEqual(index_document.command.source_version, "v1")
        self.assertEqual(index_document.command.title, " Meeting notes ")
        self.assertEqual(index_document.command.body, " Prepare next meeting ")

        relation_update_response = client.put(
            f"/indexing/documents/{DOCUMENT_ID}/folder-relations",
            json={
                "tenant": " tenant-1 ",
                "source_version": " v2 ",
                "folder_ids": [f" {FOLDER_ID} "],
            },
        )

        self.assertEqual(relation_update_response.status_code, 204)
        self.assertEqual(relation_update_response.content, b"")
        self.assertIsNotNone(update_document_folder_relations.command)
        self.assertEqual(update_document_folder_relations.command.tenant, "tenant-1")
        self.assertEqual(
            update_document_folder_relations.command.document_id,
            DOCUMENT_ID,
        )
        self.assertEqual(
            update_document_folder_relations.command.source_version,
            "v2",
        )
        self.assertEqual(
            update_document_folder_relations.command.folder_ids,
            (FOLDER_ID,),
        )

        delete_response = client.delete(
            f"/indexing/documents/{DOCUMENT_ID}",
        )

        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(delete_response.content, b"")
        self.assertIsNotNone(delete_document_index.deleted)
        self.assertEqual(delete_document_index.deleted.document_id, DOCUMENT_ID)

        delete_normalized_response = client.delete(
            f"/indexing/documents/ {DOCUMENT_ID} ",
        )

        self.assertEqual(delete_normalized_response.status_code, 204)
        self.assertEqual(delete_normalized_response.content, b"")
        self.assertIsNotNone(delete_document_index.deleted)
        self.assertEqual(delete_document_index.deleted.document_id, DOCUMENT_ID)

        delete_with_blank_document_id_response = client.delete(
            "/indexing/documents/%20",
        )

        self.assertEqual(delete_with_blank_document_id_response.status_code, 422)

        index_folder_response = client.post(
            "/indexing/folders",
            json={
                "folder": {
                    "tenant": "tenant-1",
                    "folder_id": FOLDER_ID,
                    "source_version": "folder-v1",
                    "created_at": SOURCE_CREATED_AT,
                    "updated_at": SOURCE_UPDATED_AT,
                    "name": "Startup",
                    "path": "/Company/Startup",
                    "description": "Startup docs",
                }
            },
        )

        self.assertEqual(index_folder_response.status_code, 200)
        self.assertEqual(
            index_folder_response.json()["folder"]["folder_id"],
            FOLDER_ID,
        )
        self.assertEqual(
            index_folder_response.json()["folder"]["source_version"],
            "folder-v1",
        )
        self.assertIsNotNone(index_folder.command)
        self.assertEqual(index_folder.command.name, "Startup")
        self.assertEqual(index_folder.command.created_at, SOURCE_CREATED_AT)
        self.assertEqual(index_folder.command.updated_at, SOURCE_UPDATED_AT)

        naive_folder_timestamp_response = client.post(
            "/indexing/folders",
            json={
                "folder": {
                    "tenant": "tenant-1",
                    "folder_id": FOLDER_ID,
                    "source_version": "folder-v1",
                    "created_at": "2026-05-01T10:00:00",
                    "updated_at": SOURCE_UPDATED_AT,
                    "name": "Startup",
                }
            },
        )

        self.assertEqual(naive_folder_timestamp_response.status_code, 422)

        blank_folder_name_response = client.post(
            "/indexing/folders",
            json={
                "folder": {
                    "tenant": "tenant-1",
                    "folder_id": FOLDER_ID,
                    "source_version": "folder-v1",
                    "created_at": SOURCE_CREATED_AT,
                    "updated_at": SOURCE_UPDATED_AT,
                    "name": "   ",
                }
            },
        )

        self.assertEqual(blank_folder_name_response.status_code, 422)

        delete_folder_response = client.delete(
            f"/indexing/folders/{FOLDER_ID}",
        )

        self.assertEqual(delete_folder_response.status_code, 204)
        self.assertEqual(delete_folder_response.content, b"")
        self.assertIsNotNone(delete_folder_index.deleted)
        self.assertEqual(delete_folder_index.deleted.folder_id, FOLDER_ID)

        delete_folder_normalized_response = client.delete(
            f"/indexing/folders/ {FOLDER_ID} ",
        )

        self.assertEqual(delete_folder_normalized_response.status_code, 204)
        self.assertEqual(delete_folder_normalized_response.content, b"")
        self.assertIsNotNone(delete_folder_index.deleted)
        self.assertEqual(delete_folder_index.deleted.folder_id, FOLDER_ID)

    def test_retrieval_routes_are_not_public_api(self) -> None:
        use_cases = APIUseCases(
            index_document=FakeIndexDocumentUseCase(),
            delete_document_index=FakeDeleteDocumentIndexUseCase(),
            update_document_folder_relations=FakeUpdateDocumentFolderRelationsUseCase(),
            index_folder=FakeIndexFolderUseCase(),
            delete_folder_index=FakeDeleteFolderIndexUseCase(),
            run_task=FakeRunTaskUseCase(),
            get_task=FakeGetTaskUseCase(),
            remove_task_input=FakeRemoveTaskInputUseCase(),
            record_action_result=FakeRecordActionResultUseCase(),
        )
        client = TestClient(create_app(use_cases, settings=APISettings()))

        for path in (
            "/retrieval/search",
            "/retrieval/answer",
            "/retrieval/folder-recommendations",
            "/retrieval/runs",
            "/retrieval/runs/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        ):
            response = client.post(path, json={})
            if path.startswith("/retrieval/runs"):
                response = client.get(path)
            self.assertEqual(response.status_code, 404)

    def test_task_routes_call_use_cases(self) -> None:
        run_task = FakeRunTaskUseCase()
        get_task = FakeGetTaskUseCase()
        record_action_result = FakeRecordActionResultUseCase()
        remove_task_input = FakeRemoveTaskInputUseCase()
        app = FastAPI()
        app.include_router(
            create_tasks_router(
                run_task=run_task,
                get_task=get_task,
                remove_task_input=remove_task_input,
                record_action_result=record_action_result,
            )
        )
        client = TestClient(app)

        create_response = client.post(
            "/tasks",
            json={
                "tenant": "tenant-1",
                "request": "Summarize the document",
                "context": {
                    "requested_at": REQUESTED_AT,
                    "document_id": DOCUMENT_ID,
                    "folder_id": FOLDER_ID,
                },
            },
        )

        self.assertEqual(create_response.status_code, 200)
        created_task_id = create_response.json()["task"]["task_id"]
        self.assertRegex(
            created_task_id,
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        )
        self.assertEqual(create_response.json()["task"]["status"], "clarification_required")
        self.assertEqual(create_response.json()["task"]["analysis"]["message"], "Task accepted.")
        self.assertIsNotNone(run_task.command)
        self.assertIsInstance(run_task.command, CreateTaskCommand)
        self.assertEqual(run_task.command.context.requested_at, REQUESTED_AT)
        self.assertEqual(run_task.command.context.document_id, DOCUMENT_ID)
        self.assertEqual(run_task.command.context.folder_id, FOLDER_ID)
        self.assertNotIn("requested_at", create_response.json()["task"])
        self.assertEqual(
            create_response.json()["task"]["context"]["document_id"],
            DOCUMENT_ID,
        )
        self.assertEqual(
            create_response.json()["task"]["inputs"][0]["input_text"],
            "Summarize the document",
        )
        self.assertEqual(create_response.json()["task"]["jobs"], [])
        self.assertIsNone(create_response.json()["task"]["result"])
        task_input_id = create_response.json()["task"]["inputs"][0]["task_input_id"]
        get_task.snapshot.task_id = created_task_id

        blank_tenant_response = client.post(
            "/tasks",
            json={
                "tenant": " ",
                "request": "Summarize the document",
            },
        )

        self.assertEqual(blank_tenant_response.status_code, 422)

        blank_request_response = client.post(
            "/tasks",
            json={
                "tenant": "tenant-1",
                "request": " ",
            },
        )

        self.assertEqual(blank_request_response.status_code, 422)

        invalid_requested_at_response = client.post(
            "/tasks",
            json={
                "tenant": "tenant-1",
                "request": "Summarize the document",
                "requested_at": "not-a-date",
            },
        )

        self.assertEqual(invalid_requested_at_response.status_code, 422)

        invalid_context_response = client.post(
            "/tasks",
            json={
                "tenant": "tenant-1",
                "request": "Summarize the document",
                "context": {},
            },
        )

        self.assertEqual(invalid_context_response.status_code, 422)

        append_response = client.post(
            f"/tasks/{created_task_id}/inputs",
            json={
                "request": "Narrow it down to startup notes",
                "context": {"requested_at": REQUESTED_AT},
            },
        )

        self.assertEqual(append_response.status_code, 200)
        self.assertIsInstance(run_task.command, AppendTaskInputCommand)
        self.assertEqual(run_task.command.task_id, created_task_id)
        self.assertEqual(run_task.command.context.requested_at, REQUESTED_AT)

        naive_append_response = client.post(
            f"/tasks/{created_task_id}/inputs",
            json={
                "request": "Use the last local draft",
                "context": {"requested_at": "2026-05-17T09:30:00"},
            },
        )

        self.assertEqual(naive_append_response.status_code, 422)

        missing_append_task_id = "99999999-9999-4999-8999-999999999999"
        run_task.missing_task_ids.add(missing_append_task_id)
        missing_append_response = client.post(
            f"/tasks/{missing_append_task_id}/inputs",
            json={
                "request": "Narrow it down to startup notes",
            },
        )

        self.assertEqual(missing_append_response.status_code, 404)

        remove_response = client.delete(f"/tasks/inputs/{task_input_id}")

        self.assertEqual(remove_response.status_code, 200)
        self.assertIsNotNone(remove_task_input.removed)
        self.assertEqual(remove_task_input.removed.task_input_id, task_input_id)

        invalid_remove_response = client.delete("/tasks/inputs/not-a-uuid")

        self.assertEqual(invalid_remove_response.status_code, 422)

        record_response = client.post(
            "/tasks/actions/result",
            json={
                "result": {
                    "action_id": ACTION_ID,
                    "action_type": "move_document",
                    "outcome": "succeeded",
                    "output": {
                        "moved_document_type": "document",
                        "moved_document_id": DOCUMENT_ID,
                        "target_folder_id": FOLDER_ID,
                    },
                },
            },
        )

        self.assertEqual(record_response.status_code, 200)
        self.assertEqual(record_response.json()["recorded"], True)
        self.assertEqual(record_response.json()["task"]["status"], "completed")
        self.assertIsNotNone(record_action_result.recorded)
        self.assertEqual(record_action_result.recorded.action_id, ACTION_ID)
        self.assertEqual(
            record_action_result.recorded.output.moved_document_id,
            DOCUMENT_ID,
        )

        get_response = client.get(f"/tasks/{created_task_id}")

        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["task"]["task_id"], created_task_id)

        missing_task_response = client.get("/tasks/99999999-9999-4999-8999-999999999999")

        self.assertEqual(missing_task_response.status_code, 404)

        invalid_task_id_response = client.get("/tasks/missing-task")

        self.assertEqual(invalid_task_id_response.status_code, 422)

        invalid_outcome_response = client.post(
            "/tasks/actions/result",
            json={
                "result": {
                    "action_id": ACTION_ID_2,
                    "outcome": "not-a-valid-outcome",
                },
            },
        )

        self.assertEqual(invalid_outcome_response.status_code, 422)

        missing_outcome_response = client.post(
            "/tasks/actions/result",
            json={
                "result": {
                    "action_id": ACTION_ID_3,
                },
            },
        )

        self.assertEqual(missing_outcome_response.status_code, 422)

        blank_action_id_response = client.post(
            "/tasks/actions/result",
            json={
                "result": {
                    "action_id": " ",
                    "outcome": "succeeded",
                },
            },
        )

        self.assertEqual(blank_action_id_response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
