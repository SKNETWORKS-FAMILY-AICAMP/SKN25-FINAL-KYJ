from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_core.api import APISettings, APIUseCases, create_app
from ai_core.api.routes import create_indexing_router, create_retrieval_router, create_tasks_router
from ai_core.application.models.actions import HostActionResult
from ai_core.application.models.queries import AIQuery
from ai_core.application.models.results import (
    FolderRecommendation,
    FolderRecommendationResult,
    GeneratedTextResult,
)
from ai_core.application.models.retrieval import RetrievalResult
from ai_core.application.models.tasks import TaskAnalysis, TaskRequest, TaskSnapshot, TaskStatus
from ai_core.common.validation import require_non_blank
from ai_core.domain.chunks import DocumentChunk
from ai_core.domain.documents import SourceDocument
from ai_core.domain.folders import IndexedFolder


def make_chunk(chunk_id: str = "doc-1:chunk:0", text: str = "meeting notes") -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        entity_type="document",
        entity_id="doc-1",
        version="v1",
        chunk_id=chunk_id,
        text=text,
        chunk_index=0,
        start_offset=0,
        end_offset=len(text),
        folder_ids=("folder-1",),
        tags=("meeting",),
    )


class FakeIndexDocumentUseCase:
    def __init__(self) -> None:
        self.document: SourceDocument | None = None

    def execute(self, document: SourceDocument) -> list[DocumentChunk]:
        self.document = document
        return [make_chunk(text=document.full_text)]


class FakeDeleteDocumentIndexUseCase:
    def __init__(self) -> None:
        self.deleted: tuple[str, str, str] | None = None

    def execute(self, *, tenant: str, entity_type: str, entity_id: str) -> None:
        require_non_blank(tenant, "tenant")
        require_non_blank(entity_type, "entity_type")
        require_non_blank(entity_id, "entity_id")
        self.deleted = (tenant, entity_type, entity_id)


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
                folder=IndexedFolder(
                    tenant=document.tenant,
                    folder_id="folder-1",
                    name="Meetings",
                    path="/Work/Meetings",
                ),
                reason="Folder vector is close to the document.",
                score=0.82,
            )
        )


class FakeRunTaskUseCase:
    def __init__(self) -> None:
        self.request: TaskRequest | None = None

    def execute(self, request: TaskRequest) -> TaskSnapshot:
        self.request = request
        return TaskSnapshot(
            task_id=request.task_id,
            tenant=request.tenant,
            request=request.request,
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message="Task accepted."),
            user_id=request.user_id,
            request_id=request.request_id,
            metadata=dict(request.context),
        )


class FakeRecordActionResultUseCase:
    def __init__(self) -> None:
        self.recorded: tuple[str, str, HostActionResult] | None = None

    def execute(self, *, tenant: str, task_id: str, result: HostActionResult) -> None:
        self.recorded = (tenant, task_id, result)


class ApiRouteTests(unittest.TestCase):
    def test_create_app_registers_routes(self) -> None:
        use_cases = APIUseCases(
            index_document=FakeIndexDocumentUseCase(),
            delete_document_index=FakeDeleteDocumentIndexUseCase(),
            run_task=FakeRunTaskUseCase(),
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
        app = FastAPI()
        app.include_router(
            create_indexing_router(
                index_document=index_document,
                delete_document_index=delete_document_index,
            )
        )
        client = TestClient(app)

        index_response = client.post(
            "/indexing/documents",
            json={
                "document": {
                    "tenant": "tenant-1",
                    "entity_type": "document",
                    "entity_id": "doc-1",
                    "version": "v1",
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                    "folder_ids": ["folder-1"],
                }
            },
        )

        self.assertEqual(index_response.status_code, 200)
        self.assertEqual(index_response.json(), {"indexed_chunk_count": 1})
        self.assertIsNotNone(index_document.document)
        self.assertEqual(index_document.document.entity_id, "doc-1")

        delete_response = client.post(
            "/indexing/documents/delete",
            json={
                "tenant": "tenant-1",
                "entity_type": "document",
                "entity_id": "doc-1",
            },
        )

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json(), {"deleted": True})
        self.assertEqual(delete_document_index.deleted, ("tenant-1", "document", "doc-1"))

        delete_with_metadata_response = client.post(
            "/indexing/documents/delete",
            json={
                "tenant": "tenant-1",
                "entity_type": "document",
                "entity_id": "doc-1",
                "metadata": {"request_id": "req-1"},
            },
        )

        self.assertEqual(delete_with_metadata_response.status_code, 422)

        delete_with_blank_tenant_response = client.post(
            "/indexing/documents/delete",
            json={
                "tenant": "",
                "entity_type": "document",
                "entity_id": "doc-1",
            },
        )

        self.assertEqual(delete_with_blank_tenant_response.status_code, 422)

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
                "request_context": {"tenant": "tenant-1", "user_id": "user-1"},
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
                    "entity_type": "document",
                    "entity_id": "doc-1",
                    "version": "v1",
                    "title": "Meeting notes",
                    "body": "Prepare next meeting",
                }
            },
        )

        self.assertEqual(recommend_response.status_code, 200)
        self.assertEqual(recommend_response.json()["primary"]["folder"]["folder_id"], "folder-1")
        self.assertEqual(recommend_response.json()["confidence"], 0.82)
        self.assertIsNotNone(recommend_folder.document)
        self.assertEqual(recommend_folder.document.entity_id, "doc-1")

    def test_task_routes_call_use_cases(self) -> None:
        run_task = FakeRunTaskUseCase()
        record_action_result = FakeRecordActionResultUseCase()
        app = FastAPI()
        app.include_router(
            create_tasks_router(
                run_task=run_task,
                record_action_result=record_action_result,
            )
        )
        client = TestClient(app)

        create_response = client.post(
            "/tasks",
            json={
                "task_id": "task-1",
                "tenant": "tenant-1",
                "request": "Summarize the document",
                "user_id": "user-1",
                "context": {"source": "websocket"},
            },
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["task"]["task_id"], "task-1")
        self.assertEqual(create_response.json()["task"]["status"], "clarification_required")
        self.assertEqual(create_response.json()["task"]["analysis"]["message"], "Task accepted.")
        self.assertIsNotNone(run_task.request)
        self.assertEqual(run_task.request.context["source"], "websocket")

        blank_tenant_response = client.post(
            "/tasks",
            json={
                "task_id": "task-2",
                "tenant": " ",
                "request": "Summarize the document",
            },
        )

        self.assertEqual(blank_tenant_response.status_code, 422)

        blank_request_response = client.post(
            "/tasks",
            json={
                "task_id": "task-2",
                "tenant": "tenant-1",
                "request": " ",
            },
        )

        self.assertEqual(blank_request_response.status_code, 422)

        record_response = client.post(
            "/tasks/actions/result",
            json={
                "tenant": "tenant-1",
                "task_id": "task-1",
                "result": {
                    "action_id": "action-1",
                    "action_type": "move_document",
                    "outcome": "succeeded",
                    "output": {
                        "moved_entity_type": "document",
                        "moved_entity_id": "doc-1",
                        "target_folder_id": "folder-1",
                    },
                },
            },
        )

        self.assertEqual(record_response.status_code, 200)
        self.assertEqual(record_response.json(), {"recorded": True})
        self.assertIsNotNone(record_action_result.recorded)
        self.assertEqual(record_action_result.recorded[2].action_id, "action-1")
        self.assertEqual(
            record_action_result.recorded[2].output.moved_entity_id,
            "doc-1",
        )

        invalid_outcome_response = client.post(
            "/tasks/actions/result",
            json={
                "tenant": "tenant-1",
                "task_id": "task-1",
                "result": {
                    "action_id": "action-2",
                    "outcome": "not-a-valid-outcome",
                },
            },
        )

        self.assertEqual(invalid_outcome_response.status_code, 422)

        missing_outcome_response = client.post(
            "/tasks/actions/result",
            json={
                "tenant": "tenant-1",
                "task_id": "task-1",
                "result": {
                    "action_id": "action-3",
                },
            },
        )

        self.assertEqual(missing_outcome_response.status_code, 422)

        blank_action_id_response = client.post(
            "/tasks/actions/result",
            json={
                "tenant": "tenant-1",
                "task_id": "task-1",
                "result": {
                    "action_id": " ",
                    "outcome": "succeeded",
                },
            },
        )

        self.assertEqual(blank_action_id_response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
