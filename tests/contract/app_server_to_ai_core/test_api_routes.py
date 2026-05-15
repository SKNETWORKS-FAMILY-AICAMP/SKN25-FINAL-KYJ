from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from foldmind_ai_core.adapters.inbound.http.routers.indexing import create_indexing_router
from foldmind_ai_core.adapters.inbound.http.routers.retrieval import create_retrieval_router
from foldmind_ai_core.adapters.inbound.http.routers.tasks import create_tasks_router
from foldmind_ai_core.application.errors import NoCandidatesError, ResourceNotFoundError
from foldmind_ai_core.bootstrap.app_factory import APISettings, APIUseCases, create_app
from foldmind_ai_core.domain.generation.results import (
    FolderRecommendation,
    FolderRecommendationResult,
    GeneratedTextResult,
)
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.reference.folders import SourceFolder
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.retrieval.results import RetrievalResult, RetrievedFolder
from foldmind_ai_core.domain.workflow.actions import HostActionResult
from foldmind_ai_core.domain.workflow.tasks import (
    TaskAnalysis,
    TaskAppendRequest,
    TaskCreationRequest,
    TaskRequestEntry,
    TaskSnapshot,
    TaskStatus,
)

DOCUMENT_ID = "11111111-1111-4111-8111-111111111111"
FOLDER_ID = "22222222-2222-4222-8222-222222222222"
TASK_ID = "55555555-5555-4555-8555-555555555555"
ACTION_ID = "66666666-6666-4666-8666-666666666666"
ACTION_ID_2 = "77777777-7777-4777-8777-777777777777"
ACTION_ID_3 = "88888888-8888-4888-8888-888888888888"


def make_chunk(chunk_id: str = "doc-1:chunk:0", text: str = "meeting notes") -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id="doc-1",
        source_version="v1",
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


class FakeIndexDocumentUseCase:
    def __init__(self) -> None:
        self.document: SourceDocument | None = None

    def execute(self, document: SourceDocument) -> list[DocumentChunk]:
        self.document = document
        return [make_chunk(text=document.full_text)]


class FakeDeleteDocumentIndexUseCase:
    def __init__(self) -> None:
        self.deleted: str | None = None

    def execute(self, *, document_id: str) -> None:
        self.deleted = document_id


class FakeIndexFolderUseCase:
    def __init__(self) -> None:
        self.folder: SourceFolder | None = None

    def execute(self, folder: SourceFolder) -> RetrievedFolder:
        self.folder = folder
        return RetrievedFolder(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
        )


class FakeDeleteFolderIndexUseCase:
    def __init__(self) -> None:
        self.deleted: str | None = None

    def execute(self, *, folder_id: str) -> None:
        self.deleted = folder_id


class FakeSearchDocumentsUseCase:
    def __init__(self) -> None:
        self.query: AIQuery | None = None

    def execute(self, query: AIQuery) -> list[RetrievalResult]:
        self.query = query
        return [RetrievalResult(chunk=make_chunk(), score=0.75)]


class FakeAnswerQuestionUseCase:
    def __init__(self) -> None:
        self.query: AIQuery | None = None

    def execute(self, query: AIQuery) -> GeneratedTextResult:
        self.query = query
        return GeneratedTextResult(
            text="Answer based on meeting notes.",
            citations=[RetrievalResult(chunk=make_chunk(), score=0.75)],
        )


class FakeRecommendFolderUseCase:
    def __init__(self) -> None:
        self.document: SourceDocument | None = None

    def execute(self, document: SourceDocument) -> FolderRecommendationResult:
        self.document = document
        return FolderRecommendationResult(
            primary=FolderRecommendation(
                folder_id="folder-1",
                reason="Folder vector is close to the document.",
                score=0.82,
            )
        )


class FakeRecommendFolderNoCandidatesUseCase:
    def execute(self, document: SourceDocument) -> FolderRecommendationResult:
        raise NoCandidatesError("No folder candidates found.")


class FakeRunTaskUseCase:
    def __init__(self) -> None:
        self.request: TaskCreationRequest | TaskAppendRequest | None = None

    def execute(self, request: TaskCreationRequest | TaskAppendRequest) -> TaskSnapshot:
        self.request = request
        task_id = request.task_id if isinstance(request, TaskAppendRequest) else TASK_ID
        tenant = "tenant-1" if isinstance(request, TaskAppendRequest) else request.tenant
        return TaskSnapshot(
            task_id=task_id,
            tenant=tenant,
            request=request.request,
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message="Task accepted."),
            requests=[
                TaskRequestEntry(
                    task_request_id=request.task_request_id,
                    task_id=task_id,
                    request=request.request,
                    position=0,
                )
            ],
        )


class FakeGetTaskUseCase:
    def __init__(self) -> None:
        self.snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Summarize the document",
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message="Task accepted."),
        )

    def execute(self, *, task_id: str) -> TaskSnapshot:
        if task_id != self.snapshot.task_id:
            raise ResourceNotFoundError(f"Task not found: {task_id}")
        return self.snapshot


class FakeRecordActionResultUseCase:
    def __init__(self) -> None:
        self.recorded: HostActionResult | None = None

    def execute(self, *, result: HostActionResult) -> TaskSnapshot:
        self.recorded = result
        return TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Summarize the document",
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Task completed."),
            current_action_id=result.action_id,
        )


class FakeRemoveTaskRequestUseCase:
    def __init__(self) -> None:
        self.removed: str | None = None

    def execute(
        self,
        *,
        task_request_id: str,
    ) -> TaskSnapshot:
        self.removed = task_request_id
        return TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="",
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message="Task has no active requests."),
            requests=[
                TaskRequestEntry(
                    task_request_id=task_request_id,
                    task_id=TASK_ID,
                    request="Summarize the document",
                    position=0,
                )
            ],
        )


class ApiRouteTests(unittest.TestCase):
    def test_create_app_registers_routes(self) -> None:
        use_cases = APIUseCases(
            index_document=FakeIndexDocumentUseCase(),
            delete_document_index=FakeDeleteDocumentIndexUseCase(),
            index_folder=FakeIndexFolderUseCase(),
            delete_folder_index=FakeDeleteFolderIndexUseCase(),
            run_task=FakeRunTaskUseCase(),
            get_task=FakeGetTaskUseCase(),
            remove_task_request=FakeRemoveTaskRequestUseCase(),
            record_action_result=FakeRecordActionResultUseCase(),
            search_documents=FakeSearchDocumentsUseCase(),
            answer_question=FakeAnswerQuestionUseCase(),
            recommend_folder=FakeRecommendFolderUseCase(),
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
        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(search_response.json()["results"][0]["chunk_id"], "doc-1:chunk:0")

    def test_indexing_routes_call_use_cases(self) -> None:
        index_document = FakeIndexDocumentUseCase()
        delete_document_index = FakeDeleteDocumentIndexUseCase()
        index_folder = FakeIndexFolderUseCase()
        delete_folder_index = FakeDeleteFolderIndexUseCase()
        app = FastAPI()
        app.include_router(
            create_indexing_router(
                index_document=index_document,
                delete_document_index=delete_document_index,
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
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                    "folder_ids": [FOLDER_ID],
                }
            },
        )

        self.assertEqual(index_response.status_code, 200)
        self.assertEqual(index_response.json(), {"indexed_chunk_count": 1})
        self.assertIsNotNone(index_document.document)
        self.assertEqual(index_document.document.document_id, DOCUMENT_ID)

        delete_response = client.post(
            "/indexing/documents/delete",
            json={
                "document_id": DOCUMENT_ID,
            },
        )

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json(), {"deleted": True})
        self.assertEqual(delete_document_index.deleted, DOCUMENT_ID)

        delete_with_metadata_response = client.post(
            "/indexing/documents/delete",
            json={
                "document_id": DOCUMENT_ID,
                "metadata": {"request_id": "req-1"},
            },
        )

        self.assertEqual(delete_with_metadata_response.status_code, 422)

        delete_with_blank_document_id_response = client.post(
            "/indexing/documents/delete",
            json={
                "document_id": "",
            },
        )

        self.assertEqual(delete_with_blank_document_id_response.status_code, 422)

        index_folder_response = client.post(
            "/indexing/folders",
            json={
                "folder": {
                    "tenant": "tenant-1",
                    "folder_id": FOLDER_ID,
                    "source_version": "folder-v1",
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
        self.assertIsNotNone(index_folder.folder)
        self.assertEqual(index_folder.folder.name, "Startup")

        delete_folder_response = client.post(
            "/indexing/folders/delete",
            json={"folder_id": FOLDER_ID},
        )

        self.assertEqual(delete_folder_response.status_code, 200)
        self.assertEqual(delete_folder_response.json(), {"deleted": True})
        self.assertEqual(delete_folder_index.deleted, FOLDER_ID)

    def test_retrieval_routes_call_use_cases(self) -> None:
        search_documents = FakeSearchDocumentsUseCase()
        answer_question = FakeAnswerQuestionUseCase()
        recommend_folder = FakeRecommendFolderUseCase()
        app = FastAPI()
        app.include_router(
            create_retrieval_router(
                search_documents=search_documents,
                answer_question=answer_question,
                recommend_folder=recommend_folder,
            )
        )
        client = TestClient(app)

        query_payload = {
            "query": {
                "text": "Find the last meeting notes",
                "request_context": {"tenant": "tenant-1"},
            }
        }
        search_response = client.post("/retrieval/search", json=query_payload)

        self.assertEqual(search_response.status_code, 200)
        self.assertEqual(search_response.json()["results"][0]["chunk_id"], "doc-1:chunk:0")
        self.assertIsNotNone(search_documents.query)
        self.assertEqual(search_documents.query.request_context.tenant, "tenant-1")

        answer_response = client.post("/retrieval/answer", json=query_payload)

        self.assertEqual(answer_response.status_code, 200)
        self.assertEqual(answer_response.json()["text"], "Answer based on meeting notes.")
        self.assertEqual(answer_response.json()["citations"][0]["score"], 0.75)
        self.assertIsNotNone(answer_question.query)
        self.assertEqual(answer_question.query.text, "Find the last meeting notes")

        missing_tenant_response = client.post(
            "/retrieval/search",
            json={"query": {"text": "Find the last meeting notes"}},
        )

        self.assertEqual(missing_tenant_response.status_code, 422)

        blank_tenant_response = client.post(
            "/retrieval/search",
            json={
                "query": {
                    "text": "Find the last meeting notes",
                    "request_context": {"tenant": "   "},
                }
            },
        )

        self.assertEqual(blank_tenant_response.status_code, 422)

        blank_query_response = client.post(
            "/retrieval/search",
            json={
                "query": {
                    "text": " ",
                    "request_context": {"tenant": "tenant-1"},
                }
            },
        )

        self.assertEqual(blank_query_response.status_code, 422)

        recommend_response = client.post(
            "/retrieval/folder-recommendations",
            json={
                "document": {
                    "tenant": "tenant-1",
                    "document_type": "document",
                    "document_id": DOCUMENT_ID,
                    "source_version": "v1",
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                }
            },
        )

        self.assertEqual(recommend_response.status_code, 200)
        self.assertEqual(recommend_response.json()["primary"]["folder_id"], "folder-1")
        self.assertEqual(recommend_response.json()["confidence"], 0.82)
        self.assertIsNotNone(recommend_folder.document)
        self.assertEqual(recommend_folder.document.document_id, DOCUMENT_ID)

        no_candidates_app = FastAPI()
        no_candidates_app.include_router(
            create_retrieval_router(
                search_documents=search_documents,
                answer_question=answer_question,
                recommend_folder=FakeRecommendFolderNoCandidatesUseCase(),
            )
        )
        no_candidates_response = TestClient(no_candidates_app).post(
            "/retrieval/folder-recommendations",
            json={
                "document": {
                    "tenant": "tenant-1",
                    "document_type": "document",
                    "document_id": DOCUMENT_ID,
                    "source_version": "v1",
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                }
            },
        )

        self.assertEqual(no_candidates_response.status_code, 404)

    def test_task_routes_call_use_cases(self) -> None:
        run_task = FakeRunTaskUseCase()
        get_task = FakeGetTaskUseCase()
        record_action_result = FakeRecordActionResultUseCase()
        remove_task_request = FakeRemoveTaskRequestUseCase()
        app = FastAPI()
        app.include_router(
            create_tasks_router(
                run_task=run_task,
                get_task=get_task,
                remove_task_request=remove_task_request,
                record_action_result=record_action_result,
            )
        )
        client = TestClient(app)

        create_response = client.post(
            "/tasks",
            json={
                "tenant": "tenant-1",
                "request": "Summarize the document",
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
        self.assertIsNotNone(run_task.request)
        self.assertIsInstance(run_task.request, TaskCreationRequest)
        self.assertEqual(create_response.json()["task"]["requests"][0]["request"], "Summarize the document")
        task_request_id = create_response.json()["task"]["requests"][0]["task_request_id"]
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

        append_response = client.post(
            f"/tasks/{created_task_id}/requests",
            json={
                "request": "Narrow it down to startup notes",
            },
        )

        self.assertEqual(append_response.status_code, 200)
        self.assertIsInstance(run_task.request, TaskAppendRequest)
        self.assertEqual(run_task.request.task_id, created_task_id)

        remove_response = client.delete(f"/tasks/requests/{task_request_id}")

        self.assertEqual(remove_response.status_code, 200)
        self.assertEqual(remove_task_request.removed, task_request_id)

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

        missing_task_response = client.get("/tasks/missing-task")

        self.assertEqual(missing_task_response.status_code, 404)

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
