from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from foldmind_ai_core.adapters.inbound.http.routers.indexing import create_indexing_router
from foldmind_ai_core.adapters.inbound.http.routers.tasks import create_tasks_router
from foldmind_ai_core.bootstrap.api_services import APIApplicationServices
from foldmind_ai_core.bootstrap.app_factory import create_app
from foldmind_ai_core.bootstrap.settings import APISettings
from foldmind_ai_core.core.application.models.indexing import (
    DeleteDocumentIndexCommand,
    DeleteFolderIndexCommand,
    IndexDocumentCommand,
)
from foldmind_ai_core.core.application.models.task_commands import (
    AppendTaskInputCommand,
    CreateTaskCommand,
    GetTaskQuery,
    RecordActionResultCommand,
    RemoveTaskInputCommand,
)
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.models.indexing import (
    IndexDocumentResult,
)
from foldmind_ai_core.core.application.models.task_results import (
    RecordActionResult,
)
from foldmind_ai_core.core.domain.models.host_actions import HostActionResult
from foldmind_ai_core.core.domain.models.folder_sources import (
    FolderSourceIdentity,
    SourceFolder,
)
from foldmind_ai_core.core.domain.models.tasks import (
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


class FakeDocumentIndexingService:
    def __init__(self) -> None:
        self.command: IndexDocumentCommand | None = None
        self.deleted: DeleteDocumentIndexCommand | None = None

    async def index_document(self, command: IndexDocumentCommand) -> IndexDocumentResult:
        self.command = command
        return IndexDocumentResult(indexed_chunk_count=1)

    async def delete_document(self, command: DeleteDocumentIndexCommand) -> None:
        self.deleted = command


class FakeFolderIndexingService:
    def __init__(self) -> None:
        self.folder: SourceFolder | None = None
        self.deleted: DeleteFolderIndexCommand | None = None

    async def index_folder(self, folder: SourceFolder) -> FolderSourceIdentity:
        self.folder = folder
        return FolderSourceIdentity(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
        )

    async def delete_folder(self, command: DeleteFolderIndexCommand) -> None:
        self.deleted = command


class FakeTaskWorkflowService:
    def __init__(self) -> None:
        self.created: CreateTaskCommand | None = None
        self.appended: AppendTaskInputCommand | None = None
        self.removed: RemoveTaskInputCommand | None = None
        self.recorded: HostActionResult | None = None
        self.missing_task_ids: set[str] = set()
        self.snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Summarize the document",
            context=TaskContext(requested_at=REQUESTED_AT),
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message="Task accepted."),
        )

    async def create_task(self, command: CreateTaskCommand) -> TaskSnapshot:
        self.created = command
        return _task_snapshot(
            task_id=TASK_ID,
            tenant=command.tenant,
            request=command.request,
            context=command.context,
        )

    async def append_task_input(
        self,
        command: AppendTaskInputCommand,
    ) -> TaskSnapshot:
        self.appended = command
        if command.task_id in self.missing_task_ids:
            raise ResourceNotFoundError(f"Task not found: {command.task_id}")
        return _task_snapshot(
            task_id=command.task_id,
            tenant="tenant-1",
            request=command.request,
            context=command.context,
        )

    async def get_task(self, query: GetTaskQuery) -> TaskSnapshot:
        if query.task_id != self.snapshot.task_id:
            raise ResourceNotFoundError(f"Task not found: {query.task_id}")
        return self.snapshot

    async def record_action_result(
        self,
        command: RecordActionResultCommand,
    ) -> RecordActionResult:
        self.recorded = command.result
        return RecordActionResult(
            recorded=True,
            task=TaskSnapshot(
                task_id=TASK_ID,
                tenant="tenant-1",
                request="Summarize the document",
                context=TaskContext(requested_at=REQUESTED_AT),
                status=TaskStatus.COMPLETED,
                analysis=TaskAnalysis(message="Task completed."),
                current_action_id=command.result.action_id,
            ),
        )

    async def remove_task_input(
        self,
        command: RemoveTaskInputCommand,
    ) -> TaskSnapshot:
        self.removed = command
        return TaskSnapshot(
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


def _task_snapshot(
    *,
    task_id: str,
    tenant: str,
    request: str,
    context: TaskContext,
) -> TaskSnapshot:
    return TaskSnapshot(
        task_id=task_id,
        tenant=tenant,
        request=request,
        context=context,
        status=TaskStatus.CLARIFICATION_REQUIRED,
        analysis=TaskAnalysis(message="Task accepted."),
        inputs=[
            TaskInputEntry(
                task_input_id="99999999-9999-4999-8999-000000000000",
                task_id=task_id,
                input_text=request,
                context=context,
                position=0,
            )
        ],
    )


class ApiRouteTests(unittest.TestCase):
    def test_create_app_registers_routes(self) -> None:
        application_services = APIApplicationServices(
            document_indexing=FakeDocumentIndexingService(),
            folder_indexing=FakeFolderIndexingService(),
            task_workflow=FakeTaskWorkflowService(),
        )
        app = create_app(
            application_services,
            settings=APISettings(cors_origins=("http://localhost:3000",)),
        )
        client = TestClient(app)

        health_response = client.get("/health")

        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.json(), {"status": "ok"})

    def test_indexing_routes_call_application_services(self) -> None:
        document_indexing = FakeDocumentIndexingService()
        folder_indexing = FakeFolderIndexingService()
        app = FastAPI()
        app.include_router(
            create_indexing_router(
                document_indexing=document_indexing,
                folder_indexing=folder_indexing,
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
        self.assertIsNotNone(document_indexing.command)
        self.assertEqual(document_indexing.command.document.document_id, DOCUMENT_ID)
        self.assertEqual(document_indexing.command.document.created_at, SOURCE_CREATED_AT)
        self.assertEqual(document_indexing.command.document.updated_at, SOURCE_UPDATED_AT)

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

        self.assertEqual(document_with_relation_response.status_code, 200)
        self.assertIsNotNone(document_indexing.command)
        self.assertEqual(document_indexing.command.folder_ids, (FOLDER_ID,))

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
        self.assertIsNotNone(document_indexing.command)
        self.assertIsNone(document_indexing.command.document.document_type)

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
        self.assertIsNotNone(document_indexing.command)
        self.assertEqual(document_indexing.command.document.tenant, "tenant-1")
        self.assertEqual(document_indexing.command.document.document_type, "document")
        self.assertEqual(document_indexing.command.document.document_id, DOCUMENT_ID)
        self.assertEqual(document_indexing.command.document.source_version, "v1")
        self.assertEqual(document_indexing.command.document.title, " Meeting notes ")
        self.assertEqual(document_indexing.command.document.body, " Prepare next meeting ")

        delete_response = client.delete(
            f"/indexing/documents/{DOCUMENT_ID}",
        )

        self.assertEqual(delete_response.status_code, 204)
        self.assertEqual(delete_response.content, b"")
        self.assertIsNotNone(document_indexing.deleted)
        self.assertEqual(document_indexing.deleted.document_id, DOCUMENT_ID)

        delete_normalized_response = client.delete(
            f"/indexing/documents/ {DOCUMENT_ID} ",
        )

        self.assertEqual(delete_normalized_response.status_code, 204)
        self.assertEqual(delete_normalized_response.content, b"")
        self.assertIsNotNone(document_indexing.deleted)
        self.assertEqual(document_indexing.deleted.document_id, DOCUMENT_ID)

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
        self.assertIsNotNone(folder_indexing.folder)
        self.assertEqual(folder_indexing.folder.name, "Startup")
        self.assertEqual(folder_indexing.folder.created_at, SOURCE_CREATED_AT)
        self.assertEqual(folder_indexing.folder.updated_at, SOURCE_UPDATED_AT)

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
        self.assertIsNotNone(folder_indexing.deleted)
        self.assertEqual(folder_indexing.deleted.folder_id, FOLDER_ID)

        delete_folder_normalized_response = client.delete(
            f"/indexing/folders/ {FOLDER_ID} ",
        )

        self.assertEqual(delete_folder_normalized_response.status_code, 204)
        self.assertEqual(delete_folder_normalized_response.content, b"")
        self.assertIsNotNone(folder_indexing.deleted)
        self.assertEqual(folder_indexing.deleted.folder_id, FOLDER_ID)

    def test_retrieval_routes_are_not_public_api(self) -> None:
        application_services = APIApplicationServices(
            document_indexing=FakeDocumentIndexingService(),
            folder_indexing=FakeFolderIndexingService(),
            task_workflow=FakeTaskWorkflowService(),
        )
        client = TestClient(create_app(application_services, settings=APISettings()))

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

    def test_task_routes_call_application_services(self) -> None:
        task_workflow = FakeTaskWorkflowService()
        app = FastAPI()
        app.include_router(
            create_tasks_router(
                task_workflow=task_workflow,
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
        self.assertIsNotNone(task_workflow.created)
        self.assertIsInstance(task_workflow.created, CreateTaskCommand)
        self.assertEqual(task_workflow.created.context.requested_at, REQUESTED_AT)
        self.assertEqual(task_workflow.created.context.document_id, DOCUMENT_ID)
        self.assertEqual(task_workflow.created.context.folder_id, FOLDER_ID)
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
        task_workflow.snapshot.task_id = created_task_id

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
        self.assertIsInstance(task_workflow.appended, AppendTaskInputCommand)
        self.assertEqual(task_workflow.appended.task_id, created_task_id)
        self.assertEqual(task_workflow.appended.context.requested_at, REQUESTED_AT)

        naive_append_response = client.post(
            f"/tasks/{created_task_id}/inputs",
            json={
                "request": "Use the last local draft",
                "context": {"requested_at": "2026-05-17T09:30:00"},
            },
        )

        self.assertEqual(naive_append_response.status_code, 422)

        missing_append_task_id = "99999999-9999-4999-8999-999999999999"
        task_workflow.missing_task_ids.add(missing_append_task_id)
        missing_append_response = client.post(
            f"/tasks/{missing_append_task_id}/inputs",
            json={
                "request": "Narrow it down to startup notes",
            },
        )

        self.assertEqual(missing_append_response.status_code, 404)

        remove_response = client.delete(f"/tasks/inputs/{task_input_id}")

        self.assertEqual(remove_response.status_code, 200)
        self.assertIsNotNone(task_workflow.removed)
        self.assertEqual(task_workflow.removed.task_input_id, task_input_id)

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
        self.assertIsNotNone(task_workflow.recorded)
        self.assertEqual(task_workflow.recorded.action_id, ACTION_ID)
        self.assertEqual(
            task_workflow.recorded.output.moved_document_id,
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
