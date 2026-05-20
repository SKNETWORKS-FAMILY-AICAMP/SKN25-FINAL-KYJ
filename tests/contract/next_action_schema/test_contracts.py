from __future__ import annotations

import json
import unittest
from dataclasses import is_dataclass
from enum import Enum
from pathlib import Path
from typing import get_args, get_type_hints

from pydantic import BaseModel, ValidationError

import foldmind_ai_core.adapters.inbound.http.dtos as api_dto_package
from foldmind_ai_core.adapters.inbound.http.dtos.actions import (
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
from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO
from foldmind_ai_core.adapters.inbound.http.dtos.documents import (
    RetrievedDocumentDTO,
    RetrievedFolderDTO,
    SourceDocumentDTO,
    SourceFolderDTO,
)
from foldmind_ai_core.adapters.inbound.http.dtos.indexing import IndexDocumentRequest
from foldmind_ai_core.adapters.inbound.http.dtos.queries import RetrievalQueryDTO
from foldmind_ai_core.adapters.inbound.http.dtos.retrieval import (
    FolderRecommendationDTO,
    RetrievalResultDTO,
)
from foldmind_ai_core.adapters.inbound.http.dtos.tasks import (
    AppendTaskInputRequest,
    CreateTaskRequest,
    TaskAnalysisDTO,
    TaskSnapshotDTO,
    TaskSnapshotResponse,
)
from foldmind_ai_core.adapters.inbound.http.dtos.workflow_outputs import (
    AssistantClarificationDTO,
    DocumentRecommendationDTO,
    DocumentRecommendationResultDTO,
    DocumentSearchItemDTO,
    DocumentSearchResultDTO,
    DraftResultDTO,
    FolderRecommendationResultDTO,
    RelatedRecommendationItemDTO,
    RelatedRecommendationResultDTO,
)
from foldmind_ai_core.adapters.inbound.http.mappers.actions import (
    host_action_dto_from_result,
    host_action_result_command_from_dto,
)
from foldmind_ai_core.adapters.inbound.http.mappers.documents import (
    index_document_command_from_dto,
    index_folder_command_from_dto,
)
from foldmind_ai_core.adapters.inbound.http.mappers.indexing import (
    index_document_command_from_request,
)
from foldmind_ai_core.adapters.inbound.http.mappers.queries import (
    retrieval_query_from_dto,
)
from foldmind_ai_core.adapters.inbound.http.mappers.tasks import (
    append_task_command_from_request,
    create_task_command_from_request,
    task_snapshot_response_from_result,
)
from foldmind_ai_core.adapters.outbound.workflow_runtime.checkpoint_codec import (
    workflow_state_from_checkpoint,
    workflow_state_to_checkpoint,
)
from foldmind_ai_core.adapters.outbound.workflow_runtime.graph_state import GraphState
from foldmind_ai_core.adapters.outbound.workflow_runtime.workflow_checkpoint import (
    CHECKPOINT_STATE_VERSION,
    WorkflowCheckpointState,
)
from foldmind_ai_core.core.application.models.llm import LLMMessage
from foldmind_ai_core.core.application.commands.workflow import (
    CreateDocumentOutputCommand,
    CreateFolderOutputCommand,
    HostActionResultCommand,
    LinkDocumentsOutputCommand,
    MoveDocumentOutputCommand,
    UpdateDocumentOutputCommand,
)
from foldmind_ai_core.core.application.factories.workflow_results import (
    host_action_item_result_from_domain,
    task_result_from_snapshot,
)
from foldmind_ai_core.core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.core.application.services.document_retrieval_policy import (
    DocumentRetrievalConfig,
)
from foldmind_ai_core.core.application.services.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.core.application.services.relationship_scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.core.application.use_cases.retrieval.find_documents import FindDocumentsUseCase
from foldmind_ai_core.core.application.workflows.host_actions.build_context import HostActionBuildContext
from foldmind_ai_core.core.application.workflows.state.execution import (
    OutputSpec,
    StepOutcome,
    StepSpec,
    WorkflowArtifactName,
    WorkflowArtifacts,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.domain.models.generation.results import (
    DocumentSearchItem,
    DocumentSearchResult,
    GeneratedTextResult,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery, RequestContext, SearchScope
from foldmind_ai_core.core.domain.models.retrieval.results import (
    DocumentRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
    RetrievedFolder,
)
from foldmind_ai_core.core.domain.models.workflow.actions import (
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
from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskCreationInput,
    TaskFinalResult,
    TaskJob,
    TaskJobResult,
    TaskJobStatus,
    TaskOutputType,
    TaskInputEntry,
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

    def get_by_input_id(self, *, task_input_id: str) -> TaskSnapshot | None:
        return next(
            (
                snapshot
                for snapshot in self.items.values()
                for request in snapshot.inputs
                if request.task_input_id == task_input_id
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


class FakeDocumentChunkVectorStore:
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


class FakeDocumentVectorStore:
    def __init__(
        self,
        *,
        chunks: FakeDocumentChunkVectorStore,
    ) -> None:
        self.chunks = chunks

    def replace_document_chunks(
        self,
        *,
        tenant: str,
        document_id: str,
        chunks: tuple[DocumentChunk, ...],
        vectors: tuple[Vector, ...],
    ) -> None:
        self.chunks.upsert(list(chunks), list(vectors))

    def upsert_document_vector(
        self,
        *,
        projection: object,
        vector: Vector,
    ) -> None:
        raise AssertionError("Document vector writes are not expected in these tests.")

    def delete_document_chunks(
        self,
        *,
        document_id: str,
    ) -> None:
        self.chunks.delete(document_id=document_id)

    def delete_document_vector(
        self,
        *,
        document_id: str,
    ) -> None:
        raise AssertionError("Document vector deletes are not expected in these tests.")

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

    def search_documents(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[DocumentRetrievalResult]:
        return []


def make_document_vector_store(
    *,
    dense: list[RetrievalResult],
) -> FakeDocumentVectorStore:
    return FakeDocumentVectorStore(
        chunks=FakeDocumentChunkVectorStore(dense),
    )


class FakeGraphStore:
    def __init__(self, results: list[DocumentRetrievalResult]) -> None:
        self.results = results

    def replace_document_projection(
        self,
        *,
        relationships: object,
        signals: object,
    ) -> None:
        raise AssertionError("Graph projection writes are not expected in these tests.")

    def replace_document_folder_relations(self, *, projection: object) -> None:
        raise AssertionError("Graph projection writes are not expected in these tests.")

    def replace_folder_projection(self, *, relationships: object) -> None:
        raise AssertionError("Folder projection writes are not expected in these tests.")

    def replace_folder_signals(self, *, signals: object) -> None:
        raise AssertionError("Folder projection writes are not expected in these tests.")

    def delete_document(
        self,
        *,
        document_id: str,
    ) -> None:
        raise AssertionError("Graph document deletes are not expected in these tests.")

    def delete_folder(self, *, folder_id: str) -> None:
        raise AssertionError("Graph folder deletes are not expected in these tests.")

    def delete_folder_signals(self, *, folder_id: str) -> None:
        raise AssertionError("Folder signal deletes are not expected in these tests.")

    def delete_stale_folder_signals(
        self,
        *,
        folder_id: str,
        current_index_input_digest: str,
    ) -> None:
        raise AssertionError("Folder signal deletes are not expected in these tests.")

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
    documents: FakeDocumentVectorStore,
    graph: FakeGraphStore,
    config: DocumentRetrievalConfig,
) -> FindDocumentsUseCase:
    return FindDocumentsUseCase(
        retrieval=DocumentRetrievalService(
            embeddings=FakeEmbeddingProvider(),
            chunk_vectors=documents,
            document_vectors=documents,
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
        index_input_digest="index-input-v1",
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


def make_chunk_for_entity(document_id: str, chunk_id: str, text: str = "text") -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
        index_input_digest="index-input-v1",
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

        dto = host_action_dto_from_result(host_action_item_result_from_domain(action))

        self.assertEqual(dto.action_type, HostActionType.MOVE_DOCUMENT)
        self.assertIsInstance(dto.input, MoveDocumentInputDTO)
        self.assertEqual(dto.input.target_folder_id, "folder-1")

        create_folder = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create the recommended folder.",
            input=CreateFolderInput(name="창업"),
        )
        create_folder_dto = host_action_dto_from_result(
            host_action_item_result_from_domain(create_folder)
        )

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
            ),
        )
        update_document_dto = host_action_dto_from_result(
            host_action_item_result_from_domain(update_document)
        )

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
        link_documents_dto = host_action_dto_from_result(
            host_action_item_result_from_domain(link_documents)
        )

        self.assertEqual(link_documents_dto.action_type, HostActionType.LINK_DOCUMENTS)
        self.assertIsInstance(link_documents_dto.input, LinkDocumentsInputDTO)
        self.assertEqual(link_documents_dto.input.target_id, "doc-2")

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
        context = RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00")
        scope = SearchScope(document_type="document", folder_ids=("folder-1",))

        self.assertEqual(context.tenant, "tenant-1")
        self.assertEqual(scope.folder_ids, ("folder-1",))

    def test_task_snapshot_keeps_input_entries(self) -> None:
        request = TaskCreationInput(
            tenant="tenant-1",
            request="Summarize related meeting notes.",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
        )
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant=request.tenant,
            request=request.request,
            context=request.context,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
            inputs=[
                TaskInputEntry(
                    task_input_id=request.task_input_id,
                    task_id=TASK_ID,
                    input_text=request.request,
                    context=request.context,
                    position=0,
                )
            ],
        )

        self.assertEqual(snapshot.inputs[0].task_input_id, request.task_input_id)
        self.assertEqual(snapshot.status, TaskStatus.COMPLETED)

    def test_application_ports_are_structural(self) -> None:
        store: TaskRepository = InMemoryTaskRepository()
        request = TaskCreationInput(
            tenant="tenant-1",
            request="Test",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
        )
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant=request.tenant,
            request=request.request,
            context=request.context,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
        )

        store.create(snapshot)

        self.assertIs(store.get(task_id=TASK_ID), snapshot)

    def test_indexing_dto_maps_to_command_without_holding_domain_model(self) -> None:
        request = IndexDocumentRequest(
            document=SourceDocumentDTO(
                tenant="tenant-1",
                document_type="document",
                document_id=DOCUMENT_ID,
                source_version="v1",
                created_at="2026-05-01T10:00:00+09:00",
                updated_at="2026-05-02T11:00:00+09:00",
                title="Title",
                body="Body",
            )
        )

        command = index_document_command_from_request(request)

        self.assertIsInstance(request.document, SourceDocumentDTO)
        self.assertNotIsInstance(command, SourceDocument)
        self.assertEqual(command.tenant, "tenant-1")
        self.assertEqual(command.document_type, "document")
        self.assertEqual(command.document_id, DOCUMENT_ID)
        self.assertEqual(command.source_version, "v1")

    def test_api_dtos_normalize_identity_fields_before_mapping(self) -> None:
        document = index_document_command_from_dto(SourceDocumentDTO(
            tenant=" tenant-1 ",
            document_type=" document ",
            document_id=f" {DOCUMENT_ID} ",
            source_version=" v1 ",
            created_at=" 2026-05-01T10:00:00+09:00 ",
            updated_at=" 2026-05-02T11:00:00+09:00 ",
            title=" Title ",
            body=" Body ",
        ))
        folder = index_folder_command_from_dto(SourceFolderDTO(
            tenant=" tenant-1 ",
            folder_id=f" {FOLDER_ID} ",
            source_version=" folder-v1 ",
            created_at=" 2026-05-01T10:00:00+09:00 ",
            updated_at=" 2026-05-02T11:00:00+09:00 ",
            name=" Startup ",
            parent_folder_id=f" {FOLDER_ID_2} ",
        ))
        query = retrieval_query_from_dto(RetrievalQueryDTO(
            text=" Find the last meeting notes ",
            request_context={
                "tenant": " tenant-1 ",
                "requested_at": " 2026-05-17T09:30:00+09:00 ",
            },
            scope={
                "document_type": " document ",
                "document_id": f" {DOCUMENT_ID} ",
                "document_ids": [f" {DOCUMENT_ID_2} "],
                "folder_ids": [f" {FOLDER_ID} "],
                "created_at": {"gte": " 2026-05-01T00:00:00+09:00 "},
                "sort": {"field": "created_at", "direction": "desc"},
            },
            anchor={
                "document_type": " document ",
                "document_id": f" {DOCUMENT_ID} ",
                "source_version": " v1 ",
            },
        ))
        task = create_task_command_from_request(CreateTaskRequest(
            tenant=" tenant-1 ",
            request=" Summarize the document ",
            context={
                "requested_at": " 2026-05-17T09:30:00+09:00 ",
                "document_id": f" {DOCUMENT_ID} ",
                "folder_id": f" {FOLDER_ID} ",
            },
        ))
        append = append_task_command_from_request(
            request=AppendTaskInputRequest(
                request=" Narrow it down ",
                context={
                    "requested_at": " 2026-05-17T10:00:00+09:00 ",
                    "document_id": f" {DOCUMENT_ID_2} ",
                },
            ),
            task_id=f" {TASK_ID} ",
        )
        result = host_action_result_command_from_dto(HostActionResultDTO(
            action_id=f" {ACTION_ID} ",
            action_type=HostActionType.LINK_DOCUMENTS,
            outcome=HostActionResultType.SUCCEEDED,
            output=LinkDocumentsOutputDTO(
                source_type=" document ",
                source_id=f" {DOCUMENT_ID} ",
                target_type=" note ",
                target_id=f" {DOCUMENT_ID_2} ",
                relationship=" related ",
                link_id=" link-1 ",
            ),
        ))

        self.assertEqual(document.tenant, "tenant-1")
        self.assertEqual(document.document_type, "document")
        self.assertEqual(document.document_id, DOCUMENT_ID)
        self.assertEqual(document.source_version, "v1")
        self.assertEqual(document.title, " Title ")
        self.assertEqual(document.body, " Body ")
        self.assertEqual(folder.tenant, "tenant-1")
        self.assertEqual(folder.folder_id, FOLDER_ID)
        self.assertEqual(folder.source_version, "folder-v1")
        self.assertEqual(folder.parent_folder_id, FOLDER_ID_2)
        self.assertEqual(folder.name, "Startup")
        self.assertEqual(query.request_context.tenant, "tenant-1")
        self.assertEqual(query.request_context.requested_at, "2026-05-17T09:30:00+09:00")
        self.assertEqual(query.scope.document_type, "document")
        self.assertEqual(query.scope.document_id, DOCUMENT_ID)
        self.assertEqual(query.scope.document_ids, (DOCUMENT_ID_2,))
        self.assertEqual(query.scope.folder_ids, (FOLDER_ID,))
        self.assertEqual(query.scope.created_at.gte, "2026-05-01T00:00:00+09:00")
        self.assertEqual(query.scope.sort.field, "created_at")
        self.assertEqual(query.scope.sort.direction, "desc")
        self.assertEqual(query.anchor.document_type, "document")
        self.assertEqual(query.anchor.document_id, DOCUMENT_ID)
        self.assertEqual(query.anchor.source_version, "v1")
        self.assertEqual(query.text, " Find the last meeting notes ")
        self.assertEqual(task.tenant, "tenant-1")
        self.assertEqual(task.request, "Summarize the document")
        self.assertEqual(task.context.requested_at, "2026-05-17T09:30:00+09:00")
        self.assertEqual(task.context.document_id, DOCUMENT_ID)
        self.assertEqual(task.context.folder_id, FOLDER_ID)
        self.assertEqual(append.task_id, TASK_ID)
        self.assertEqual(append.request, "Narrow it down")
        self.assertEqual(append.context.requested_at, "2026-05-17T10:00:00+09:00")
        self.assertEqual(append.context.document_id, DOCUMENT_ID_2)
        self.assertIsNone(append.context.folder_id)
        self.assertEqual(result.action_id, ACTION_ID)
        self.assertEqual(result.output.source_type, "document")
        self.assertEqual(result.output.source_id, DOCUMENT_ID)
        self.assertEqual(result.output.target_type, "note")
        self.assertEqual(result.output.target_id, DOCUMENT_ID_2)
        self.assertEqual(result.output.relationship, "related")
        self.assertEqual(result.output.link_id, "link-1")

    def test_task_response_dto_maps_from_result_without_exposing_internal_model(self) -> None:
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Test",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
            metadata={
                "source": "websocket",
                "workflow_feedback": "internal replan note",
                "workflow_round": 2,
            },
        )

        response = task_snapshot_response_from_result(task_result_from_snapshot(snapshot))

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
                metadata={"source_tags": ["startup"]},
            ),
            action_id=ACTION_ID,
            status=HostActionStatus.READY,
        )
        task = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Create a document.",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
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
                            index_input_digest="index-input-v1",
                            created_at="2026-05-01T10:00:00+09:00",
                            updated_at="2026-05-02T11:00:00+09:00",
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
        self.assertEqual(graph_state["state_version"], CHECKPOINT_STATE_VERSION)
        checkpoint_payload = json.dumps(graph_state)
        self.assertIn("__foldmind_checkpoint_type__", checkpoint_payload)
        self.assertNotIn("__ai_core_checkpoint_type__", checkpoint_payload)
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
        self.assertEqual(
            restored.task.host_actions[0].input.metadata,
            {"source_tags": ["startup"]},
        )

    def test_action_result_dto_maps_to_command(self) -> None:
        result = host_action_result_command_from_dto(HostActionResultDTO(
            action_id=ACTION_ID,
            outcome="failed",
            error=" Execution failed. ",
        ))

        self.assertIsInstance(result, HostActionResultCommand)
        self.assertEqual(result.outcome, HostActionResultType.FAILED.value)
        self.assertEqual(result.error, "Execution failed.")
        self.assertIsNone(result.output)

        created = host_action_result_command_from_dto(HostActionResultDTO(
            action_id=ACTION_ID_2,
            action_type=HostActionType.CREATE_DOCUMENT,
            outcome=HostActionResultType.SUCCEEDED,
            output=CreateDocumentOutputDTO(created_document_id=DOCUMENT_ID),
        ))

        self.assertEqual(created.action_type, HostActionType.CREATE_DOCUMENT.value)
        self.assertIsInstance(created.output, CreateDocumentOutputCommand)
        self.assertEqual(created.output.created_document_id, DOCUMENT_ID)

        folder = host_action_result_command_from_dto(HostActionResultDTO(
            action_id=ACTION_ID_3,
            action_type=HostActionType.CREATE_FOLDER,
            outcome=HostActionResultType.SUCCEEDED,
            output=CreateFolderOutputDTO(folder_id=FOLDER_ID, name="창업"),
        ))

        self.assertEqual(folder.action_type, HostActionType.CREATE_FOLDER.value)
        self.assertIsInstance(folder.output, CreateFolderOutputCommand)
        self.assertEqual(folder.output.folder_id, FOLDER_ID)

        updated = host_action_result_command_from_dto(HostActionResultDTO(
            action_id=ACTION_ID_4,
            action_type=HostActionType.UPDATE_DOCUMENT,
            outcome=HostActionResultType.SUCCEEDED,
            output=UpdateDocumentOutputDTO(
                updated_document_type="document",
                updated_document_id=DOCUMENT_ID,
                source_version="v2",
            ),
        ))

        self.assertEqual(updated.action_type, HostActionType.UPDATE_DOCUMENT.value)
        self.assertIsInstance(updated.output, UpdateDocumentOutputCommand)
        self.assertEqual(updated.output.updated_document_id, DOCUMENT_ID)

        moved = host_action_result_command_from_dto(HostActionResultDTO(
            action_id=ACTION_ID_5,
            action_type=HostActionType.MOVE_DOCUMENT,
            outcome=HostActionResultType.SUCCEEDED,
            output=MoveDocumentOutputDTO(
                moved_document_type="document",
                moved_document_id=DOCUMENT_ID,
                target_folder_id=FOLDER_ID_2,
            ),
        ))

        self.assertEqual(moved.action_type, HostActionType.MOVE_DOCUMENT.value)
        self.assertIsInstance(moved.output, MoveDocumentOutputCommand)
        self.assertEqual(moved.output.target_folder_id, FOLDER_ID_2)

        linked = host_action_result_command_from_dto(HostActionResultDTO(
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
        ))

        self.assertEqual(linked.action_type, HostActionType.LINK_DOCUMENTS.value)
        self.assertIsInstance(linked.output, LinkDocumentsOutputCommand)
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
        with self.assertRaises(ValidationError):
            HostActionResultDTO(
                action_id=ACTION_ID,
                action_type=HostActionType.CREATE_DOCUMENT,
                outcome=HostActionResultType.FAILED,
                output=CreateDocumentOutputDTO(created_document_id=DOCUMENT_ID),
            )
        with self.assertRaises(ValidationError):
            HostActionResultDTO(
                action_id=ACTION_ID,
                outcome=HostActionResultType.SUCCEEDED,
                error="Unexpected error.",
            )

    def test_api_dtos_validate_blank_input_before_mapping(self) -> None:
        document = SourceDocumentDTO(
            tenant="tenant-1",
            document_type="document",
            document_id="",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="Title",
            body="Body",
        )
        query = RetrievalQueryDTO(text=" ", request_context={"tenant": "tenant-1"})
        result = HostActionResultDTO(
            action_id="",
            outcome=HostActionResultType.SUCCEEDED,
        )
        invalid_uuid_document = SourceDocumentDTO(
            tenant="tenant-1",
            document_type="document",
            document_id="doc-1",
            source_version="v1",
            created_at="2026-05-01T10:00:00+09:00",
            updated_at="2026-05-02T11:00:00+09:00",
            title="Title",
            body="Body",
        )

        with self.assertRaises(InvalidInputError):
            index_document_command_from_dto(document)

        with self.assertRaises(InvalidInputError):
            index_document_command_from_dto(invalid_uuid_document)

        with self.assertRaises(InvalidInputError):
            retrieval_query_from_dto(query)

        with self.assertRaises(InvalidInputError):
            host_action_result_command_from_dto(result)

    def test_application_models_are_plain_state_containers(self) -> None:
        context = RequestContext(tenant=" ", requested_at="2026-05-17T09:30:00+09:00")
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
        query = RetrievalQuery(
            text="   ",
            request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00"),
        )
        request = TaskCreationInput(
            tenant="tenant-1",
            request="",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
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
                ActionPlanDTO,
                AssistantClarificationDTO,
                CreateDocumentInputDTO,
                CreateDocumentOutputDTO,
                CreateFolderInputDTO,
                CreateFolderOutputDTO,
                DocumentRecommendationDTO,
                DocumentRecommendationResultDTO,
                DocumentSearchItemDTO,
                DocumentSearchResultDTO,
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
                RelatedRecommendationItemDTO,
                RelatedRecommendationResultDTO,
                RecordHostActionResultRequest,
                RetrievalResultDTO,
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
        self.assertTrue(issubclass(IndexDocumentRequest, APIDTO))
        self.assertEqual(IndexDocumentRequest.model_config["extra"], "forbid")

    def test_task_snapshot_dto_uses_final_result_and_job_summaries(self) -> None:
        self.assertEqual(set(TaskAnalysisDTO.model_fields), {"message"})

        chunk = make_chunk("doc-a:chunk:0", "answer evidence")
        answer = GeneratedTextResult(
            text="Answer.",
            citations=[RetrievalResult(chunk=chunk, score=0.9)],
        )
        action_plan = ActionPlan(summary="Plan.", steps=["create draft"])
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Test",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
            jobs=[
                TaskJob(
                    job_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                    job_type="answer",
                    round_index=0,
                    position=0,
                    status=TaskJobStatus.SUCCEEDED,
                    results=[
                        TaskJobResult(
                            result_type=str(TaskOutputType.ANSWER),
                            result=answer,
                            summary={"text": "Answer."},
                        ),
                        TaskJobResult(
                            result_type=str(TaskOutputType.ACTION_PLAN),
                            result=action_plan,
                            summary={"steps": 1},
                        ),
                    ],
                )
            ],
            result=TaskFinalResult(
                result_type=TaskOutputType.ANSWER,
                result=answer,
                title="Answer",
                metadata={"source": "workflow"},
            ),
        )

        response = task_snapshot_response_from_result(task_result_from_snapshot(snapshot))

        self.assertEqual(response.task.analysis.message, "Done.")
        self.assertIsNotNone(response.task.result)
        self.assertEqual(response.task.result.type, "answer")
        self.assertEqual(response.task.result.result.text, "Answer.")
        self.assertEqual(response.task.result.result.citations[0].chunk_id, "doc-a:chunk:0")
        self.assertEqual(response.task.result.title, "Answer")
        self.assertEqual(response.task.jobs[0].results[0].summary, {"text": "Answer."})
        self.assertEqual(response.task.jobs[0].results[1].summary, {"steps": 1})
        self.assertFalse(hasattr(response.task.jobs[0].results[0], "result"))

    def test_models_are_split_by_layer_concern(self) -> None:
        self.assertEqual(RetrievalQuery.__module__, "foldmind_ai_core.core.application.queries.retrieval")
        self.assertEqual(RetrievalResult.__module__, "foldmind_ai_core.core.domain.models.retrieval.results")
        self.assertEqual(LLMMessage.__module__, "foldmind_ai_core.core.application.models.llm")
        self.assertEqual(
            GeneratedTextResult.__module__,
            "foldmind_ai_core.core.domain.models.generation.results",
        )
        self.assertEqual(
            OutputSpec.__module__,
            "foldmind_ai_core.core.application.workflows.state.execution",
        )
        self.assertEqual(
            StepSpec.__module__,
            "foldmind_ai_core.core.application.workflows.state.execution",
        )
        self.assertEqual(
            StepOutcome.__module__,
            "foldmind_ai_core.core.application.workflows.state.execution",
        )
        self.assertEqual(
            HostActionBuildContext.__module__,
            "foldmind_ai_core.core.application.workflows.host_actions.build_context",
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
            "foldmind_ai_core.core.application.workflows.state.workflow_state",
        )
        self.assertEqual(TaskSnapshot.__module__, "foldmind_ai_core.core.domain.models.workflow.tasks")
        self.assertFalse(hasattr(api_dto_package, "WorkflowCheckpointState"))

    def test_find_documents_use_case_uses_dense_chunk_results(self) -> None:
        chunk_a = make_chunk("doc-a:chunk:0")
        chunk_b = make_chunk("doc-b:chunk:0")

        documents = make_document_vector_store(
            dense=[
                RetrievalResult(chunk=chunk_a, score=0.95),
                RetrievalResult(chunk=chunk_b, score=0.90),
            ]
        )
        results = make_find_documents_use_case(
            documents=documents,
            graph=FakeGraphStore([]),
            config=DocumentRetrievalConfig(top_k=2),
        ).execute(RetrievalQuery(text="meeting notes", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00")))

        self.assertEqual(
            [result.chunk_id for result in results.results],
            ["doc-a:chunk:0", "doc-b:chunk:0"],
        )

    def test_comprehensive_search_merges_metadata_candidates(self) -> None:
        dense = [
            RetrievalResult(
                chunk=make_chunk_for_entity("doc-a", "doc-a:chunk:dense"),
                score=0.9,
            )
        ]
        graph = [
            DocumentRetrievalResult(
                document=RetrievedDocument(
                    tenant="tenant-1",
                    document_type="document",
                    document_id="doc-c",
                    source_version="v1",
                    created_at="2026-05-01T10:00:00+09:00",
                    updated_at="2026-05-02T11:00:00+09:00",
                    snippet="graph candidate",
                ),
                score=1.0,
            )
        ]
        documents = make_document_vector_store(
            dense=[
                *dense,
                RetrievalResult(
                    chunk=make_chunk_for_entity("doc-c", "doc-c:chunk:graph"),
                    score=0.8,
                ),
            ],
        )

        results = make_find_documents_use_case(
            documents=documents,
            graph=FakeGraphStore(graph),
            config=DocumentRetrievalConfig(comprehensive_top_k=10),
        ).execute(
            RetrievalQuery(text="창업", request_context=RequestContext(tenant="tenant-1", requested_at="2026-05-17T09:30:00+09:00")),
            require_comprehensive_search=True,
        )

        self.assertEqual(
            {result.document_id for result in results.results},
            {"doc-a", "doc-c"},
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
