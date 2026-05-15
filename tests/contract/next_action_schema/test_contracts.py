from __future__ import annotations

import unittest
from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path
from typing import get_args, get_type_hints

from pydantic import BaseModel, ValidationError

import foldmind_ai_core.adapters.inbound.http.schemas as api_schema_package
from foldmind_ai_core.adapters.inbound.http.schemas.actions import (
    ActionPlanDTO,
    CreateDocumentInputDTO,
    CreateDocumentOutputDTO,
    CreateFolderInputDTO,
    CreateFolderOutputDTO,
    HostActionDTO,
    HostActionInputDTO,
    HostActionResultDTO,
    HostActionResultOutputDTO,
    LinkDocumentsInputDTO,
    LinkDocumentsOutputDTO,
    MoveDocumentInputDTO,
    MoveDocumentOutputDTO,
    RecordHostActionResultRequest,
    UpdateDocumentInputDTO,
    UpdateDocumentOutputDTO,
)
from foldmind_ai_core.adapters.inbound.http.schemas.base import APIBaseDTO
from foldmind_ai_core.adapters.inbound.http.schemas.documents import (
    RetrievedDocumentDTO,
    RetrievedFolderDTO,
    SourceDocumentDTO,
)
from foldmind_ai_core.adapters.inbound.http.schemas.indexing import IndexDocumentRequest
from foldmind_ai_core.adapters.inbound.http.schemas.queries import AIQueryDTO
from foldmind_ai_core.adapters.inbound.http.schemas.retrieval import (
    AnswerQuestionRequest,
    AssistantClarificationDTO,
    DocumentRecommendationDTO,
    DocumentRecommendationResultDTO,
    DraftResultDTO,
    FolderRecommendationDTO,
    FolderRecommendationResultDTO,
    RecommendFolderRequest,
    RecommendFolderResponse,
    RelatedRecommendationItemDTO,
    RelatedRecommendationResultDTO,
    RetrievalResultDTO,
    SearchDocumentsRequest,
    SearchDocumentsResponse,
)
from foldmind_ai_core.adapters.inbound.http.schemas.tasks import (
    TaskAnalysisDTO,
    TaskSnapshotDTO,
    TaskSnapshotResponse,
)
from foldmind_ai_core.adapters.outbound.workflow_runtime.checkpoint_codec import (
    workflow_state_from_checkpoint,
    workflow_state_to_checkpoint,
)
from foldmind_ai_core.adapters.outbound.workflow_runtime.graph_state import GraphState
from foldmind_ai_core.adapters.outbound.workflow_runtime.workflow_checkpoint import (
    WorkflowCheckpointState,
)
from foldmind_ai_core.application.dto.llm import LLMMessage
from foldmind_ai_core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.application.services.document_retrieval_policy import (
    HybridSearchConfig,
    SearchMode,
    reciprocal_rank_fusion,
)
from foldmind_ai_core.application.services.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.application.use_cases.retrieval.find_documents import FindDocumentsUseCase
from foldmind_ai_core.application.workflows.host_actions.build_context import HostActionBuildContext
from foldmind_ai_core.application.workflows.state.execution import (
    OutputSpec,
    StepOutcome,
    StepSpec,
    WorkflowArtifactName,
    WorkflowArtifacts,
    WorkflowExecutionPlan,
    WorkflowRunResult,
)
from foldmind_ai_core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.domain.generation.results import (
    AssistantResponse,
    AssistantResponseStatus,
    GeneratedTextResult,
)
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.retrieval.queries import AIQuery, RequestContext, SearchScope
from foldmind_ai_core.domain.retrieval.results import (
    DocumentRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
    RetrievedFolder,
)
from foldmind_ai_core.domain.workflow.actions import (
    ActionPlan,
    CreateDocumentInput,
    CreateDocumentOutput,
    CreateFolderInput,
    CreateFolderOutput,
    HostAction,
    HostActionInput,
    HostActionResult,
    HostActionResultType,
    HostActionStatus,
    HostActionType,
    LinkDocumentsInput,
    LinkDocumentsOutput,
    MoveDocumentInput,
    MoveDocumentOutput,
    UpdateDocumentInput,
    UpdateDocumentOutput,
)
from foldmind_ai_core.domain.workflow.tasks import (
    TaskAnalysis,
    TaskCreationRequest,
    TaskOutput,
    TaskOutputType,
    TaskRequestEntry,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.types import Metadata, Vector
from foldmind_ai_core.shared.validation import InvalidInputError

DOCUMENT_ID = "11111111-1111-4111-8111-111111111111"
DOCUMENT_ID_2 = "33333333-3333-4333-8333-333333333333"
FOLDER_ID = "22222222-2222-4222-8222-222222222222"
FOLDER_ID_2 = "44444444-4444-4444-8444-444444444444"
TASK_ID = "55555555-5555-4555-8555-555555555555"
ACTION_ID = "66666666-6666-4666-8666-666666666666"
ACTION_ID_2 = "77777777-7777-4777-8777-777777777777"
ACTION_ID_3 = "88888888-8888-4888-8888-888888888888"
ACTION_ID_4 = "99999999-9999-4999-8999-999999999999"
ACTION_ID_5 = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ACTION_ID_6 = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self.items: dict[str, TaskSnapshot] = {}

    def create(self, snapshot: TaskSnapshot) -> None:
        self.items[snapshot.task_id] = snapshot

    def get(self, *, task_id: str) -> TaskSnapshot | None:
        return self.items.get(task_id)

    def get_by_request_id(self, *, task_request_id: str) -> TaskSnapshot | None:
        return next(
            (
                snapshot
                for snapshot in self.items.values()
                for request in snapshot.requests
                if request.task_request_id == task_request_id
            ),
            None,
        )

    def get_by_action_id(self, *, action_id: str) -> TaskSnapshot | None:
        return next(
            (
                snapshot
                for snapshot in self.items.values()
                for action in snapshot.host_actions
                if action.action_id == action_id
            ),
            None,
        )

    def save(self, snapshot: TaskSnapshot) -> None:
        self.items[snapshot.task_id] = snapshot


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        return [[float(len(text))] for text in texts]


class FakeDocumentChunkVectorRepository:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.upserted: list[DocumentChunk] = []
        self.deleted: list[str] = []

    def upsert(self, chunks: list[DocumentChunk], vectors: list[Vector]) -> None:
        self.upserted.extend(chunks)

    def delete(self, *, document_id: str) -> None:
        self.deleted.append(document_id)

    def similarity_search(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return self.results[:top_k]


class FakeDocumentKeywordRepository:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.upserted: list[DocumentChunk] = []
        self.deleted: list[str] = []

    def upsert(self, chunks: list[DocumentChunk]) -> None:
        self.upserted.extend(chunks)

    def delete(self, *, document_id: str) -> None:
        self.deleted.append(document_id)

    def keyword_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return self.results[:top_k]


class FakeDocumentVectorRepository:
    def __init__(
        self,
        *,
        chunks: FakeDocumentChunkVectorRepository,
        keywords: FakeDocumentKeywordRepository | None = None,
    ) -> None:
        self.chunks = chunks
        self.keywords = keywords

    def replace_document_chunks(
        self,
        *,
        document_id: str,
        chunks: tuple[DocumentChunk, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        self.chunks.upsert(list(chunks), list(vectors))

    def upsert_keywords(self, chunks: tuple[DocumentChunk, ...]) -> None:
        if self.keywords is not None:
            self.keywords.upsert(list(chunks))

    def upsert_document_vector(
        self,
        *,
        projection: object,
        vector: Vector,
    ) -> None:
        return None

    def delete_document_chunks(
        self,
        *,
        document_id: str,
    ) -> None:
        self.chunks.delete(document_id=document_id)

    def delete_document_keywords(
        self,
        *,
        document_id: str,
    ) -> None:
        if self.keywords is not None:
            self.keywords.delete(
                document_id=document_id,
            )

    def delete_document_vector(
        self,
        *,
        document_id: str,
    ) -> None:
        return None

    def search_chunks(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return self.chunks.similarity_search(
            tenant=tenant,
            query_vector=query_vector,
            top_k=top_k,
            scope=scope,
        )

    def search_keywords(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        if self.keywords is None:
            raise InvalidInputError("keyword search requires a keyword index.")
        return self.keywords.keyword_search(
            tenant=tenant,
            query_text=query_text,
            top_k=top_k,
            scope=scope,
        )

    def search_documents(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        return []


def make_document_repositories(
    *,
    dense: list[RetrievalResult],
    keyword: list[RetrievalResult] | None = None,
) -> FakeDocumentVectorRepository:
    return FakeDocumentVectorRepository(
        chunks=FakeDocumentChunkVectorRepository(dense),
        keywords=FakeDocumentKeywordRepository(keyword) if keyword is not None else None,
    )


class FakeGraphRepository:
    def __init__(self, results: list[DocumentRetrievalResult]) -> None:
        self.results = results

    def replace_document_projection(
        self,
        *,
        relationships: object,
        concepts: object,
    ) -> None:
        pass

    def replace_folder_hierarchy(self, projection: object) -> None:
        pass

    def upsert_tag(self, projection: object) -> None:
        pass

    def delete_document(self, *, document_id: str) -> None:
        pass

    def delete_folder(self, *, folder_id: str) -> None:
        pass

    def graph_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        return self.results[:top_k]

    def document_ids_for_scope(self, *, tenant: str, scope: SearchScope) -> tuple[str, ...]:
        return scope.document_ids

    def folders_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> dict[str, tuple[RetrievedFolder, ...]]:
        return {}


def make_find_documents_use_case(
    *,
    documents: FakeDocumentVectorRepository,
    graph: FakeGraphRepository,
    config: HybridSearchConfig,
) -> FindDocumentsUseCase:
    return FindDocumentsUseCase(
        retrieval=DocumentRetrievalService(
            embeddings=FakeEmbeddingProvider(),
            chunk_vectors=documents,
            document_vectors=documents,
            keyword_repository=documents if documents.keywords is not None else None,
            graph=graph,
            config=config,
        ),
        scope_resolver=RelationshipScopeResolver(graph=graph),
    )


def make_chunk(chunk_id: str, text: str = "text") -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id=chunk_id.split("-")[0],
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


def make_chunk_for_entity(document_id: str, chunk_id: str, text: str = "text") -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
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


class ContractTests(unittest.TestCase):
    def assert_json_safe(self, value: object) -> None:
        self.assertFalse(is_dataclass(value))
        self.assertFalse(isinstance(value, Enum))
        if value is None or isinstance(value, str | int | float | bool):
            return
        if isinstance(value, list):
            for item in value:
                self.assert_json_safe(item)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                self.assertIsInstance(key, str)
                self.assert_json_safe(item)
            return
        self.fail(f"Unexpected non-primitive checkpoint value: {type(value).__name__}")

    def test_common_types_are_importable(self) -> None:
        metadata: Metadata = {"source": "unit-test"}
        vector: Vector = [0.1, 0.2, 0.3]

        self.assertEqual(metadata["source"], "unit-test")
        self.assertEqual(len(vector), 3)

    def test_host_action_accepts_typed_payload(self) -> None:
        action = HostAction(
            action_type=HostActionType.MOVE_DOCUMENT,
            summary="Move the document to the recommended folder.",
            input=MoveDocumentInput(
                document_type="document",
                document_id="doc-1",
                target_folder_id="folder-1",
            ),
        )

        self.assertEqual(action.action_type, HostActionType.MOVE_DOCUMENT)
        self.assertIsInstance(action.input, MoveDocumentInput)

        dto = HostActionDTO.from_model(action)

        self.assertEqual(dto.action_type, HostActionType.MOVE_DOCUMENT)
        self.assertIsInstance(dto.input, MoveDocumentInputDTO)
        self.assertEqual(dto.input.target_folder_id, "folder-1")

        create_folder = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create the recommended folder.",
            input=CreateFolderInput(name="창업"),
        )
        create_folder_dto = HostActionDTO.from_model(create_folder)

        self.assertEqual(create_folder_dto.action_type, HostActionType.CREATE_FOLDER)
        self.assertIsInstance(create_folder_dto.input, CreateFolderInputDTO)
        self.assertEqual(create_folder_dto.input.name, "창업")

        update_document = HostAction(
            action_type=HostActionType.UPDATE_DOCUMENT,
            summary="Update document metadata.",
            input=UpdateDocumentInput(
                document_type="document",
                document_id="doc-1",
                title="Updated title",
                tag_ids=("startup",),
            ),
        )
        update_document_dto = HostActionDTO.from_model(update_document)

        self.assertEqual(update_document_dto.action_type, HostActionType.UPDATE_DOCUMENT)
        self.assertIsInstance(update_document_dto.input, UpdateDocumentInputDTO)
        self.assertEqual(update_document_dto.input.title, "Updated title")

        link_documents = HostAction(
            action_type=HostActionType.LINK_DOCUMENTS,
            summary="Link documents.",
            input=LinkDocumentsInput(
                source_type="document",
                source_id="doc-1",
                target_type="document",
                target_id="doc-2",
            ),
        )
        link_documents_dto = HostActionDTO.from_model(link_documents)

        self.assertEqual(link_documents_dto.action_type, HostActionType.LINK_DOCUMENTS)
        self.assertIsInstance(link_documents_dto.input, LinkDocumentsInputDTO)
        self.assertEqual(link_documents_dto.input.target_id, "doc-2")

    def test_host_action_is_plain_action_state(self) -> None:
        action = HostAction(
            action_type="unsupported_action",
            summary="Run an unsupported action.",
            input=None,  # type: ignore[arg-type]
        )

        self.assertEqual(action.action_type, "unsupported_action")
        self.assertIsNone(action.input)

    def test_host_action_input_does_not_allow_untyped_dict_payload(self) -> None:
        self.assertNotIn(dict[str, object], get_args(HostActionInput))
        self.assertFalse(
            any(getattr(arg, "__origin__", None) is dict for arg in get_args(HostActionInput))
        )
        self.assertNotIn(dict[str, object], get_args(HostActionInputDTO))
        self.assertFalse(
            any(getattr(arg, "__origin__", None) is dict for arg in get_args(HostActionInputDTO))
        )

    def test_host_action_dto_matches_action_type_to_payload(self) -> None:
        schema = HostActionDTO.model_json_schema()
        input_schema = schema["properties"]["input"]

        self.assertIn("input", schema["required"])
        self.assertNotIn({"type": "null"}, input_schema["anyOf"])

        with self.assertRaises(ValidationError):
            HostActionDTO(
                action_type=HostActionType.MOVE_DOCUMENT,
                summary="Mismatch.",
                input=CreateDocumentInputDTO(title="Title", body="Body"),
            )

        with self.assertRaises(ValidationError):
            HostActionDTO(
                action_type=HostActionType.MOVE_DOCUMENT,
                summary="Null input.",
                input=None,
            )

        with self.assertRaises(ValidationError):
            HostActionDTO(
                action_type=HostActionType.MOVE_DOCUMENT,
                summary="Missing input.",
            )

    def test_query_context_and_scope_model_app_server_boundary(self) -> None:
        context = RequestContext(tenant="tenant-1")
        scope = SearchScope(document_type="document", folder_ids=("folder-1",))

        self.assertEqual(context.tenant, "tenant-1")
        self.assertEqual(scope.folder_ids, ("folder-1",))

    def test_task_snapshot_keeps_request_entries(self) -> None:
        request = TaskCreationRequest(
            tenant="tenant-1",
            request="Summarize related meeting notes.",
        )
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant=request.tenant,
            request=request.request,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
            requests=[
                TaskRequestEntry(
                    task_request_id=request.task_request_id,
                    task_id=TASK_ID,
                    request=request.request,
                    position=0,
                )
            ],
        )

        self.assertEqual(snapshot.requests[0].task_request_id, request.task_request_id)
        self.assertEqual(snapshot.status, TaskStatus.COMPLETED)

    def test_application_ports_are_structural(self) -> None:
        store: TaskRepository = InMemoryTaskRepository()
        request = TaskCreationRequest(tenant="tenant-1", request="Test")
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant=request.tenant,
            request=request.request,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
        )

        store.create(snapshot)

        self.assertIs(store.get(task_id=TASK_ID), snapshot)

    def test_indexing_dto_maps_to_domain_without_holding_domain_model(self) -> None:
        request = IndexDocumentRequest(
            document=SourceDocumentDTO(
                tenant="tenant-1",
                document_type="document",
                document_id=DOCUMENT_ID,
                source_version="v1",
                title="Title",
                body="Body",
            )
        )

        document = request.to_model()

        self.assertIsInstance(request.document, SourceDocumentDTO)
        self.assertIsInstance(document, SourceDocument)
        self.assertEqual(document.tenant, "tenant-1")
        self.assertEqual(document.document_type, "document")
        self.assertEqual(document.document_id, DOCUMENT_ID)
        self.assertEqual(document.source_version, "v1")

    def test_task_response_dto_maps_from_model_without_exposing_internal_model(self) -> None:
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Test",
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
            metadata={"source": "websocket", "workflow_round": 2},
        )

        response = TaskSnapshotResponse.from_model(snapshot)

        self.assertEqual(response.task.status, TaskStatus.COMPLETED)
        self.assertEqual(response.task.analysis.message, "Done.")
        self.assertEqual(response.task.metadata, {"source": "websocket"})

    def test_workflow_graph_state_is_json_safe_and_restores_domain_models(self) -> None:
        action = HostAction(
            action_type=HostActionType.CREATE_DOCUMENT,
            summary="Create a summary document.",
            input=CreateDocumentInput(
                title="Summary",
                body="Body",
                tag_ids=("startup",),
            ),
            action_id=ACTION_ID,
            status=HostActionStatus.READY,
        )
        task = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Create a document.",
            status=TaskStatus.READY_FOR_HOST_ACTION,
            analysis=TaskAnalysis(message="Ready."),
            host_actions=[action],
        )
        artifacts = WorkflowArtifacts()
        artifacts.write(
            WorkflowArtifactName.SUMMARY,
            GeneratedTextResult(
                text="Summary",
                citations=[
                    RetrievalResult(
                        chunk=DocumentChunk(
                            tenant="tenant-1",
                            document_type="document",
                            document_id="doc-1",
                            source_version="v1",
                            chunk_id="chunk-1",
                            chunk_index=0,
                            chunking_version="chunking-test-v1",
                            text="Evidence",
                            text_hash="hash-1",
                            start_offset=0,
                            end_offset=8,
                            embedding_model="test-embedding",
                            embedding_version="test-v1",
                            index_schema_version="schema-v1",
                        ),
                        score=0.7,
                    )
                ],
            ),
        )
        state = WorkflowState(
            task=task,
            artifacts=artifacts,
            pending_actions=[action],
        )

        graph_state = workflow_state_to_checkpoint(state)

        self.assert_json_safe(graph_state)
        self.assertEqual(
            GraphState.__module__,
            "foldmind_ai_core.adapters.outbound.workflow_runtime.graph_state",
        )
        self.assertIsInstance(graph_state["task"], dict)
        self.assertEqual(
            graph_state["pending_actions"][0]["value"]["action_type"],
            "create_document",
        )

        restored = workflow_state_from_checkpoint(graph_state)

        self.assertIsInstance(restored.task, TaskSnapshot)
        self.assertEqual(
            restored.task.host_actions[0].action_type,
            HostActionType.CREATE_DOCUMENT,
        )
        self.assertEqual(restored.task.host_actions[0].status, HostActionStatus.READY)
        self.assertEqual(restored.task.host_actions[0].input.tag_ids, ("startup",))

    def test_action_result_dto_maps_to_model(self) -> None:
        result = HostActionResultDTO(
            action_id=ACTION_ID,
            outcome="failed",
            error="Execution failed.",
        ).to_model()

        self.assertIsInstance(result, HostActionResult)
        self.assertEqual(result.outcome, HostActionResultType.FAILED)
        self.assertIsNone(result.output)

        created = HostActionResultDTO(
            action_id=ACTION_ID_2,
            action_type=HostActionType.CREATE_DOCUMENT,
            outcome=HostActionResultType.SUCCEEDED,
            output=CreateDocumentOutputDTO(created_document_id=DOCUMENT_ID),
        ).to_model()

        self.assertEqual(created.action_type, "create_document")
        self.assertIsInstance(created.output, CreateDocumentOutput)
        self.assertEqual(created.output.created_document_id, DOCUMENT_ID)

        folder = HostActionResultDTO(
            action_id=ACTION_ID_3,
            action_type=HostActionType.CREATE_FOLDER,
            outcome=HostActionResultType.SUCCEEDED,
            output=CreateFolderOutputDTO(folder_id=FOLDER_ID, name="창업"),
        ).to_model()

        self.assertEqual(folder.action_type, "create_folder")
        self.assertIsInstance(folder.output, CreateFolderOutput)
        self.assertEqual(folder.output.folder_id, FOLDER_ID)

        updated = HostActionResultDTO(
            action_id=ACTION_ID_4,
            action_type=HostActionType.UPDATE_DOCUMENT,
            outcome=HostActionResultType.SUCCEEDED,
            output=UpdateDocumentOutputDTO(
                updated_document_type="document",
                updated_document_id=DOCUMENT_ID,
                source_version="v2",
            ),
        ).to_model()

        self.assertEqual(updated.action_type, "update_document")
        self.assertIsInstance(updated.output, UpdateDocumentOutput)
        self.assertEqual(updated.output.updated_document_id, DOCUMENT_ID)

        moved = HostActionResultDTO(
            action_id=ACTION_ID_5,
            action_type=HostActionType.MOVE_DOCUMENT,
            outcome=HostActionResultType.SUCCEEDED,
            output=MoveDocumentOutputDTO(
                moved_document_type="document",
                moved_document_id=DOCUMENT_ID,
                target_folder_id=FOLDER_ID_2,
            ),
        ).to_model()

        self.assertEqual(moved.action_type, "move_document")
        self.assertIsInstance(moved.output, MoveDocumentOutput)
        self.assertEqual(moved.output.target_folder_id, FOLDER_ID_2)

        linked = HostActionResultDTO(
            action_id=ACTION_ID_6,
            action_type=HostActionType.LINK_DOCUMENTS,
            outcome=HostActionResultType.SUCCEEDED,
            output=LinkDocumentsOutputDTO(
                source_type="document",
                source_id=DOCUMENT_ID,
                target_type="document",
                target_id=DOCUMENT_ID_2,
                link_id="link-1",
            ),
        ).to_model()

        self.assertEqual(linked.action_type, "link_documents")
        self.assertIsInstance(linked.output, LinkDocumentsOutput)
        self.assertEqual(linked.output.link_id, "link-1")

    def test_action_result_output_matches_action_type(self) -> None:
        self.assertNotIn(dict[str, object], get_args(HostActionResultOutputDTO))
        self.assertFalse(
            any(
                getattr(arg, "__origin__", None) is dict
                for arg in get_args(HostActionResultOutputDTO)
            )
        )

        with self.assertRaises(ValidationError):
            HostActionResultDTO(
                action_id=ACTION_ID,
                action_type=HostActionType.MOVE_DOCUMENT,
                outcome=HostActionResultType.SUCCEEDED,
                output=CreateDocumentOutputDTO(created_document_id="doc-1"),
            )

    def test_api_dtos_validate_blank_input_before_mapping(self) -> None:
        document = SourceDocumentDTO(
            tenant="tenant-1",
            document_type="document",
            document_id="",
            source_version="v1",
            title="Title",
            body="Body",
        )
        query = AIQueryDTO(text=" ", request_context={"tenant": "tenant-1"})
        result = HostActionResultDTO(
            action_id="",
            outcome=HostActionResultType.SUCCEEDED,
        )
        invalid_uuid_document = SourceDocumentDTO(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            title="Title",
            body="Body",
        )

        with self.assertRaises(InvalidInputError):
            document.to_model()

        with self.assertRaises(InvalidInputError):
            invalid_uuid_document.to_model()

        with self.assertRaises(InvalidInputError):
            query.to_model()

        with self.assertRaises(InvalidInputError):
            result.to_model()

    def test_application_models_are_plain_state_containers(self) -> None:
        context = RequestContext(tenant=" ")
        document_input = CreateDocumentInput(title="Title", body="Body", folder_id=" ")
        move_input = MoveDocumentInput(
            document_type="document",
            document_id="",
            target_folder_id=" ",
        )
        document_output = CreateDocumentOutput(created_document_id="")
        action_result = HostActionResult(
            action_id="",
            outcome=HostActionResultType.SUCCEEDED,
        )
        query = AIQuery(
            text="   ",
            request_context=RequestContext(tenant="tenant-1"),
        )
        request = TaskCreationRequest(
            tenant="tenant-1",
            request="",
        )

        self.assertEqual(context.tenant, " ")
        self.assertEqual(document_input.folder_id, " ")
        self.assertEqual(move_input.document_id, "")
        self.assertEqual(document_output.created_document_id, "")
        self.assertEqual(action_result.action_id, "")
        self.assertEqual(query.text, "   ")
        self.assertEqual(request.request, "")

    def test_api_dtos_do_not_use_domain_models_as_fields(self) -> None:
        dto_field_types = {
            get_type_hints(dto)[field_name]
            for dto in (
                AnswerQuestionRequest,
                ActionPlanDTO,
                AssistantClarificationDTO,
                CreateDocumentInputDTO,
                CreateDocumentOutputDTO,
                CreateFolderInputDTO,
                CreateFolderOutputDTO,
                DocumentRecommendationDTO,
                DocumentRecommendationResultDTO,
                DraftResultDTO,
                FolderRecommendationDTO,
                FolderRecommendationResultDTO,
                HostActionDTO,
                RetrievedDocumentDTO,
                RetrievedFolderDTO,
                IndexDocumentRequest,
                LinkDocumentsInputDTO,
                LinkDocumentsOutputDTO,
                MoveDocumentInputDTO,
                MoveDocumentOutputDTO,
                RecommendFolderRequest,
                RecommendFolderResponse,
                RelatedRecommendationItemDTO,
                RelatedRecommendationResultDTO,
                RecordHostActionResultRequest,
                RetrievalResultDTO,
                SearchDocumentsRequest,
                SearchDocumentsResponse,
                TaskSnapshotDTO,
                TaskSnapshotResponse,
                UpdateDocumentInputDTO,
                UpdateDocumentOutputDTO,
            )
            for field_name in dto.model_fields
        }

        self.assertNotIn(SourceDocument, dto_field_types)
        self.assertNotIn(HostActionResult, dto_field_types)
        self.assertNotIn(TaskSnapshot, dto_field_types)

    def test_api_dtos_are_pydantic_models(self) -> None:
        self.assertTrue(issubclass(IndexDocumentRequest, BaseModel))
        self.assertTrue(issubclass(RecordHostActionResultRequest, BaseModel))
        self.assertTrue(issubclass(TaskSnapshotResponse, BaseModel))
        self.assertTrue(issubclass(IndexDocumentRequest, APIBaseDTO))
        self.assertEqual(IndexDocumentRequest.model_config["extra"], "forbid")

    def test_task_analysis_dto_uses_typed_result_models(self) -> None:
        self.assertEqual(set(TaskAnalysisDTO.model_fields), {"message", "outputs"})

        chunk = make_chunk("doc-a:chunk:0", "answer evidence")
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Test",
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(
                message="Done.",
                outputs=[
                    TaskOutput(
                        output_type=TaskOutputType.ANSWER,
                        result=GeneratedTextResult(
                            text="Answer.",
                            citations=[RetrievalResult(chunk=chunk, score=0.9)],
                        ),
                    ),
                    TaskOutput(
                        output_type=TaskOutputType.ACTION_PLAN,
                        result=ActionPlan(summary="Plan.", steps=["create draft"]),
                    ),
                ],
            ),
        )

        response = TaskSnapshotResponse.from_model(snapshot)
        answer_output = response.task.analysis.outputs[0]
        action_plan_output = response.task.analysis.outputs[1]

        self.assertEqual(response.task.analysis.message, "Done.")
        self.assertEqual(answer_output.type, "answer")
        self.assertEqual(answer_output.result.text, "Answer.")
        self.assertEqual(answer_output.result.citations[0].chunk_id, "doc-a:chunk:0")
        self.assertEqual(action_plan_output.type, "action_plan")
        self.assertEqual(action_plan_output.result.summary, "Plan.")
        self.assertEqual(action_plan_output.result.steps, ["create draft"])

    def test_task_output_is_plain_output_state(self) -> None:
        mismatched = TaskOutput(
            output_type=TaskOutputType.ANSWER,
            result=ActionPlan(summary="Plan.", steps=["create draft"]),
        )
        unsupported = TaskOutput(
            output_type="unsupported_output",
            result=GeneratedTextResult(text="Answer."),
        )

        self.assertEqual(mismatched.output_type, TaskOutputType.ANSWER)
        self.assertEqual(unsupported.output_type, "unsupported_output")

    def test_models_are_split_by_layer_concern(self) -> None:
        self.assertEqual(AIQuery.__module__, "foldmind_ai_core.domain.retrieval.queries")
        self.assertEqual(RetrievalResult.__module__, "foldmind_ai_core.domain.retrieval.results")
        self.assertEqual(LLMMessage.__module__, "foldmind_ai_core.application.dto.llm")
        self.assertEqual(
            GeneratedTextResult.__module__,
            "foldmind_ai_core.domain.generation.results",
        )
        self.assertEqual(AssistantResponse.__module__, "foldmind_ai_core.domain.generation.results")
        self.assertEqual(
            AssistantResponseStatus.__module__,
            "foldmind_ai_core.domain.generation.results",
        )
        self.assertEqual(
            OutputSpec.__module__,
            "foldmind_ai_core.application.workflows.state.execution",
        )
        self.assertEqual(
            StepSpec.__module__,
            "foldmind_ai_core.application.workflows.state.execution",
        )
        self.assertEqual(
            StepOutcome.__module__,
            "foldmind_ai_core.application.workflows.state.execution",
        )
        self.assertEqual(
            WorkflowRunResult.__module__,
            "foldmind_ai_core.application.workflows.state.execution",
        )
        self.assertEqual(
            HostActionBuildContext.__module__,
            "foldmind_ai_core.application.workflows.host_actions.build_context",
        )
        self.assertEqual(
            GraphState.__module__,
            "foldmind_ai_core.adapters.outbound.workflow_runtime.graph_state",
        )
        self.assertEqual(
            WorkflowCheckpointState.__module__,
            "foldmind_ai_core.adapters.outbound.workflow_runtime.workflow_checkpoint",
        )
        self.assertEqual(
            WorkflowState.__module__,
            "foldmind_ai_core.application.workflows.state.workflow_state",
        )
        self.assertEqual(TaskSnapshot.__module__, "foldmind_ai_core.domain.workflow.tasks")
        self.assertFalse(hasattr(api_schema_package, "WorkflowCheckpointState"))

    def test_assistant_response_does_not_expose_workflow_internals(self) -> None:
        response = AssistantResponse(response="Done.")
        run_result = WorkflowRunResult(plan=WorkflowExecutionPlan())

        self.assertEqual(response.response, "Done.")
        self.assertFalse(hasattr(response, "plan"))
        self.assertEqual(run_result.plan.round_index, 0)

    def test_rrf_fuses_dense_and_keyword_rankings(self) -> None:
        chunk_a = make_chunk("doc-a:chunk:0")
        chunk_b = make_chunk("doc-b:chunk:0")
        chunk_c = make_chunk("doc-c:chunk:0")

        fused = reciprocal_rank_fusion(
            [
                [
                    RetrievalResult(chunk=chunk_a, score=0.95),
                    RetrievalResult(chunk=chunk_b, score=0.90),
                ],
                [
                    RetrievalResult(chunk=chunk_b, score=12.0),
                    RetrievalResult(chunk=chunk_c, score=9.0),
                ],
            ],
            top_k=3,
            k=60,
        )

        self.assertEqual(fused[0].chunk.chunk_id, "doc-b:chunk:0")
        self.assertGreater(fused[0].score, fused[1].score)

    def test_find_documents_use_case_uses_rrf(self) -> None:
        chunk_a = make_chunk("doc-a:chunk:0")
        chunk_b = make_chunk("doc-b:chunk:0")
        dense = [
            RetrievalResult(chunk=chunk_a, score=0.95),
            RetrievalResult(chunk=chunk_b, score=0.90),
        ]
        keyword = [
            RetrievalResult(chunk=chunk_b, score=12.0),
            RetrievalResult(chunk=make_chunk("doc-c:chunk:0"), score=9.0),
        ]

        documents = make_document_repositories(dense=dense, keyword=keyword)
        results = make_find_documents_use_case(
            documents=documents,
            graph=FakeGraphRepository([]),
            config=HybridSearchConfig(
                mode=SearchMode.HYBRID,
                top_k=2,
                dense_top_k=2,
                keyword_top_k=2,
            ),
        ).execute(AIQuery(text="meeting notes", request_context=RequestContext(tenant="tenant-1")))

        self.assertEqual(
            [result.chunk.chunk_id for result in results],
            ["doc-b:chunk:0", "doc-a:chunk:0"],
        )

    def test_find_documents_use_case_uses_hybrid_when_keyword_store_is_available(self) -> None:
        chunk_a = make_chunk("doc-a:chunk:0")
        chunk_b = make_chunk("doc-b:chunk:0")

        documents = make_document_repositories(
            dense=[
                RetrievalResult(chunk=chunk_a, score=0.95),
                RetrievalResult(chunk=chunk_b, score=0.90),
            ],
            keyword=[
                RetrievalResult(chunk=chunk_b, score=12.0),
            ],
        )
        results = make_find_documents_use_case(
            documents=documents,
            graph=FakeGraphRepository([]),
            config=HybridSearchConfig(mode=SearchMode.HYBRID, top_k=1),
        ).execute(
            AIQuery(text="meeting notes", request_context=RequestContext(tenant="tenant-1"))
        )

        self.assertEqual(results[0].chunk.chunk_id, "doc-b:chunk:0")

    def test_comprehensive_search_merges_metadata_candidates(self) -> None:
        dense = [
            RetrievalResult(
                chunk=make_chunk_for_entity("doc-a", "doc-a:chunk:dense"),
                score=0.9,
            )
        ]
        keyword = [
            RetrievalResult(
                chunk=make_chunk_for_entity("doc-b", "doc-b:chunk:keyword"),
                score=3.0,
            )
        ]
        graph = [
            DocumentRetrievalResult(
                document=RetrievedDocument(
                    tenant="tenant-1",
                    document_type="document",
                    document_id="doc-c",
                    source_version="v1",
                    snippet="graph candidate",
                ),
                score=1.0,
            )
        ]
        documents = make_document_repositories(
            dense=[
                *dense,
                RetrievalResult(
                    chunk=make_chunk_for_entity("doc-c", "doc-c:chunk:graph"),
                    score=0.8,
                ),
            ],
            keyword=keyword,
        )

        results = make_find_documents_use_case(
            documents=documents,
            graph=FakeGraphRepository(graph),
            config=HybridSearchConfig(mode=SearchMode.HYBRID, comprehensive_top_k=10),
        ).execute(
            AIQuery(text="창업", request_context=RequestContext(tenant="tenant-1")),
            require_comprehensive_search=True,
        )

        self.assertEqual(
            {result.chunk.document_id for result in results},
            {"doc-a", "doc-b", "doc-c"},
        )

    def test_assistant_agents_do_not_depend_on_use_cases(self) -> None:
        project_root = next(
            parent for parent in Path(__file__).resolve().parents if (parent / "src").exists()
        )
        agents_dir = (
            project_root / "src" / "foldmind_ai_core" / "application" / "agents"
        )

        for path in agents_dir.glob("*.py"):
            self.assertNotIn("application.use_cases", path.read_text())


if __name__ == "__main__":
    unittest.main()
