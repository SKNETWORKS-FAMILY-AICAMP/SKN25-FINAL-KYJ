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
from foldmind_ai_core.adapters.inbound.http.dtos.documents import (
    RetrievedDocumentDTO,
    RetrievedFolderDTO,
    SourceDocumentDTO,
    SourceFolderDTO,
)
from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO
from foldmind_ai_core.adapters.inbound.http.dtos.indexing import IndexDocumentRequest
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
    GeneratedTextDTO,
    RelatedRecommendationItemDTO,
    RelatedRecommendationResultDTO,
)
from foldmind_ai_core.adapters.inbound.http.mappers.actions import (
    host_action_dto_from_domain,
    host_action_result_from_dto,
)
from foldmind_ai_core.adapters.inbound.http.mappers.documents import (
    index_document_command_from_dto,
    source_folder_from_dto,
)
from foldmind_ai_core.adapters.inbound.http.mappers.indexing import (
    index_document_command_from_request,
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
from foldmind_ai_core.core.application.ports.outbound.repository.task_repository import (
    TaskRepositoryPort,
)
from foldmind_ai_core.core.application.models.search import (
    RequestContext,
    SearchScope,
)
from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.services.retrieval.document_retrieval_service import (
    DocumentRetrievalService,
)
from foldmind_ai_core.core.application.services.retrieval.document_search_service import (
    DocumentSearchService,
)
from foldmind_ai_core.core.application.services.retrieval.policy import (
    DocumentRetrievalConfig,
)
from foldmind_ai_core.core.application.services.retrieval.scope_resolver import (
    RelationshipScopeResolver,
)
from foldmind_ai_core.core.application.workflows.host_actions.build_context import (
    HostActionBuildContext,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    OutputSpec,
    StepOutcome,
    StepSpec,
    WorkflowArtifactName,
    WorkflowArtifacts,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.models.generation import (
    GeneratedTextResult,
)
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.application.models.retrieval import (
    DocumentRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.models.host_actions import (
    ActionPlan,
    CreateDocumentInput,
    CreateDocumentOutput,
    CreateFolderOutput,
    CreateFolderInput,
    HostAction,
    HostActionInput,
    HostActionResult,
    HostActionResultType,
    HostActionStatus,
    HostActionType,
    LinkDocumentsOutput,
    LinkDocumentsInput,
    MoveDocumentOutput,
    MoveDocumentInput,
    UpdateDocumentOutput,
    UpdateDocumentInput,
)
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskFinalResult,
    TaskInputEntry,
    TaskJob,
    TaskJobResult,
    TaskJobStatus,
    TaskOutputType,
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


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        return [[float(len(text))] for text in texts]


class FakeDocumentChunkVectorStore:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.upserted: list[object] = []
        self.deleted: list[str] = []

    def upsert(self, chunks: list[object], vectors: list[Vector]) -> None:
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
        chunks: tuple[object, ...],
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
        tenant: str,
        document_id: str,
    ) -> None:
        self.chunks.delete(document_id=document_id)

    def delete_document_vector(
        self,
        *,
        tenant: str,
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


class FakeDocumentSourceRepository:
    async def get_current_document_sources(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> tuple[object, ...]:
        return ()

    async def document_ids_for_scope(
        self,
        *,
        tenant: str,
        document_type: str | None,
        document_id: str | None,
        document_ids: tuple[str, ...],
        created_at: object,
        updated_at: object,
        metadata_filter: object,
    ) -> tuple[str, ...]:
        if document_ids:
            return document_ids
        if document_id is not None:
            return (document_id,)
        return ()

    async def search_titles_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        document_type: str | None,
        document_id: str | None,
        document_ids: tuple[str, ...],
        created_at: object,
        updated_at: object,
        metadata_filter: object,
    ) -> tuple[object, ...]:
        return ()


class FakeDocumentProjectionRepository:
    async def get_first_chunks_for_documents(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
        limit: int,
    ) -> tuple[object, ...]:
        return ()

    async def search_chunks_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        document_id: str | None,
        document_ids: tuple[str, ...],
    ) -> tuple[object, ...]:
        return ()


class FakeDocumentRelationRepository:
    async def document_ids_for_folders(
        self,
        *,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        return ()


class FakeFolderSourceRepository:
    async def search_names_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        folder_ids: tuple[str, ...],
        created_at: object,
        updated_at: object,
    ) -> tuple[object, ...]:
        return ()

    async def search_descriptions_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        folder_ids: tuple[str, ...],
        created_at: object,
        updated_at: object,
    ) -> tuple[object, ...]:
        return ()


class FakeRetrievalReadSession:
    document_sources = FakeDocumentSourceRepository()
    document_projections = FakeDocumentProjectionRepository()
    document_relations = FakeDocumentRelationRepository()
    folder_sources = FakeFolderSourceRepository()


class FakeRetrievalReadSessionScope:
    async def __aenter__(self) -> FakeRetrievalReadSession:
        return FakeRetrievalReadSession()

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class FakeRetrievalReadSessionProvider:
    def session(self) -> FakeRetrievalReadSessionScope:
        return FakeRetrievalReadSessionScope()


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
        tenant: str,
        document_id: str,
    ) -> None:
        raise AssertionError("Graph document deletes are not expected in these tests.")

    def delete_folder(self, *, tenant: str, folder_id: str) -> None:
        raise AssertionError("Graph folder deletes are not expected in these tests.")

    def delete_folder_signals(self, *, tenant: str, folder_id: str) -> None:
        raise AssertionError("Folder signal deletes are not expected in these tests.")

    def delete_stale_folder_signals(
        self,
        *,
        tenant: str,
        folder_id: str,
        current_folder_signal_input_digest: str,
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
    ) -> dict[str, tuple[SourceFolder, ...]]:
        return {}


def make_document_search_service(
    *,
    documents: FakeDocumentVectorStore,
    graph: FakeGraphStore,
    config: DocumentRetrievalConfig,
) -> DocumentSearchService:
    return DocumentSearchService(
        retrieval=DocumentRetrievalService(
            embeddings=FakeEmbeddingProvider(),
            chunk_vectors=documents,
            document_vectors=documents,
            graph=graph,
            retrieval_reads=FakeRetrievalReadSessionProvider(),
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
        document_index_input_digest="index-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        chunk_id=chunk_id,
        chunk_index=0,
        text=text,
        start_offset=0,
        end_offset=len(text),
    )


def make_chunk_for_entity(
    document_id: str,
    chunk_id: str,
    text: str = "text",
) -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        document_type="document",
        document_id=document_id,
        source_version="v1",
        document_index_input_digest="index-input-v1",
        created_at="2026-05-01T10:00:00+09:00",
        updated_at="2026-05-02T11:00:00+09:00",
        chunk_id=chunk_id,
        chunk_index=0,
        text=text,
        start_offset=0,
        end_offset=len(text),
    )


class ContractTests(unittest.IsolatedAsyncioTestCase):
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

        dto = host_action_dto_from_domain(action)

        self.assertEqual(dto.action_type, HostActionType.MOVE_DOCUMENT)
        self.assertIsInstance(dto.input, MoveDocumentInputDTO)
        self.assertEqual(dto.input.target_folder_id, "folder-1")

        create_folder = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create the recommended folder.",
            input=CreateFolderInput(name="Research"),
        )
        create_folder_dto = host_action_dto_from_domain(create_folder)

        self.assertEqual(create_folder_dto.action_type, HostActionType.CREATE_FOLDER)
        self.assertIsInstance(create_folder_dto.input, CreateFolderInputDTO)
        self.assertEqual(create_folder_dto.input.name, "Research")
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
        task_input_id = "task-input-1"
        request_text = "Summarize related meeting notes."
        context = TaskContext(requested_at="2026-05-17T09:30:00+09:00")
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request=request_text,
            context=context,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
            inputs=[
                TaskInputEntry(
                    task_input_id=task_input_id,
                    task_id=TASK_ID,
                    input_text=request_text,
                    context=context,
                    position=0,
                )
            ],
        )

        self.assertEqual(snapshot.inputs[0].task_input_id, task_input_id)
        self.assertEqual(snapshot.status, TaskStatus.COMPLETED)

    def test_application_ports_are_structural(self) -> None:
        store: TaskRepositoryPort = InMemoryTaskRepository()
        request_text = "Test"
        context = TaskContext(requested_at="2026-05-17T09:30:00+09:00")
        snapshot = TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request=request_text,
            context=context,
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
        self.assertEqual(command.document.tenant, "tenant-1")
        self.assertEqual(command.document.document_type, "document")
        self.assertEqual(command.document.document_id, DOCUMENT_ID)
        self.assertEqual(command.document.source_version, "v1")

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
        folder = source_folder_from_dto(SourceFolderDTO(
            tenant=" tenant-1 ",
            folder_id=f" {FOLDER_ID} ",
            source_version=" folder-v1 ",
            created_at=" 2026-05-01T10:00:00+09:00 ",
            updated_at=" 2026-05-02T11:00:00+09:00 ",
            name=" Startup ",
            parent_folder_id=f" {FOLDER_ID_2} ",
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
        result = host_action_result_from_dto(HostActionResultDTO(
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

        self.assertEqual(document.document.tenant, "tenant-1")
        self.assertEqual(document.document.document_type, "document")
        self.assertEqual(document.document.document_id, DOCUMENT_ID)
        self.assertEqual(document.document.source_version, "v1")
        self.assertEqual(document.document.title, " Title ")
        self.assertEqual(document.document.body, " Body ")
        self.assertEqual(folder.tenant, "tenant-1")
        self.assertEqual(folder.folder_id, FOLDER_ID)
        self.assertEqual(folder.source_version, "folder-v1")
        self.assertEqual(folder.parent_folder_id, FOLDER_ID_2)
        self.assertEqual(folder.name, "Startup")
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

        response = task_snapshot_response_from_result(snapshot)

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
                            document_index_input_digest="index-input-v1",
                            created_at="2026-05-01T10:00:00+09:00",
                            updated_at="2026-05-02T11:00:00+09:00",
                            chunk_id="chunk-1",
                            chunk_index=0,
                            text="Evidence",
                            start_offset=0,
                            end_offset=8,
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

    def test_action_result_dto_maps_to_domain_result(self) -> None:
        result = host_action_result_from_dto(HostActionResultDTO(
            action_id=ACTION_ID,
            outcome="failed",
            error=" Execution failed. ",
        ))

        self.assertIsInstance(result, HostActionResult)
        self.assertEqual(result.outcome, HostActionResultType.FAILED)
        self.assertEqual(result.error, "Execution failed.")
        self.assertIsNone(result.output)

        created = host_action_result_from_dto(HostActionResultDTO(
            action_id=ACTION_ID_2,
            action_type=HostActionType.CREATE_DOCUMENT,
            outcome=HostActionResultType.SUCCEEDED,
            output=CreateDocumentOutputDTO(created_document_id=DOCUMENT_ID),
        ))

        self.assertEqual(created.action_type, HostActionType.CREATE_DOCUMENT)
        self.assertIsInstance(created.output, CreateDocumentOutput)
        self.assertEqual(created.output.created_document_id, DOCUMENT_ID)

        folder = host_action_result_from_dto(HostActionResultDTO(
            action_id=ACTION_ID_3,
            action_type=HostActionType.CREATE_FOLDER,
            outcome=HostActionResultType.SUCCEEDED,
            output=CreateFolderOutputDTO(folder_id=FOLDER_ID, name="창업"),
        ))

        self.assertEqual(folder.action_type, HostActionType.CREATE_FOLDER)
        self.assertIsInstance(folder.output, CreateFolderOutput)
        self.assertEqual(folder.output.folder_id, FOLDER_ID)

        updated = host_action_result_from_dto(HostActionResultDTO(
            action_id=ACTION_ID_4,
            action_type=HostActionType.UPDATE_DOCUMENT,
            outcome=HostActionResultType.SUCCEEDED,
            output=UpdateDocumentOutputDTO(
                updated_document_type="document",
                updated_document_id=DOCUMENT_ID,
                source_version="v2",
            ),
        ))

        self.assertEqual(updated.action_type, HostActionType.UPDATE_DOCUMENT)
        self.assertIsInstance(updated.output, UpdateDocumentOutput)
        self.assertEqual(updated.output.updated_document_id, DOCUMENT_ID)

        moved = host_action_result_from_dto(HostActionResultDTO(
            action_id=ACTION_ID_5,
            action_type=HostActionType.MOVE_DOCUMENT,
            outcome=HostActionResultType.SUCCEEDED,
            output=MoveDocumentOutputDTO(
                moved_document_type="document",
                moved_document_id=DOCUMENT_ID,
                target_folder_id=FOLDER_ID_2,
            ),
        ))

        self.assertEqual(moved.action_type, HostActionType.MOVE_DOCUMENT)
        self.assertIsInstance(moved.output, MoveDocumentOutput)
        self.assertEqual(moved.output.target_folder_id, FOLDER_ID_2)

        linked = host_action_result_from_dto(HostActionResultDTO(
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

        self.assertEqual(linked.action_type, HostActionType.LINK_DOCUMENTS)
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
            host_action_result_from_dto(result)

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
            request_context=RequestContext(
                tenant="tenant-1",
                requested_at="2026-05-17T09:30:00+09:00",
            ),
        )

        self.assertEqual(context.tenant, " ")
        self.assertEqual(document_input.folder_id, " ")
        self.assertEqual(move_input.document_id, "")
        self.assertEqual(document_output.created_document_id, "")
        self.assertEqual(action_result.action_id, "")
        self.assertEqual(query.text, "   ")

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

        response = task_snapshot_response_from_result(snapshot)

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
        self.assertEqual(
            RetrievalQuery.__module__,
            "foldmind_ai_core.core.application.models.retrieval",
        )
        self.assertEqual(
            RetrievalResult.__module__,
            "foldmind_ai_core.core.application.models.retrieval",
        )
        self.assertEqual(
            LLMMessage.__module__,
            "foldmind_ai_core.core.application.models.llm",
        )
        self.assertEqual(
            GeneratedTextResult.__module__,
            "foldmind_ai_core.core.application.models.generation",
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
        self.assertEqual(
            TaskSnapshot.__module__,
            "foldmind_ai_core.core.domain.models.tasks",
        )
        self.assertFalse(hasattr(api_dto_package, "WorkflowCheckpointState"))

    async def test_document_search_service_uses_dense_chunk_results(self) -> None:
        chunk_a = make_chunk("doc-a:chunk:0")
        chunk_b = make_chunk("doc-b:chunk:0")

        documents = make_document_vector_store(
            dense=[
                RetrievalResult(chunk=chunk_a, score=0.95),
                RetrievalResult(chunk=chunk_b, score=0.90),
            ]
        )
        results = await make_document_search_service(
            documents=documents,
            graph=FakeGraphStore([]),
            config=DocumentRetrievalConfig(top_k=2),
        ).search(
            RetrievalQuery(
                text="meeting notes",
                request_context=RequestContext(
                    tenant="tenant-1",
                    requested_at="2026-05-17T09:30:00+09:00",
                ),
            )
        )

        self.assertEqual(
            [result.chunk.chunk_id for result in results],
            ["doc-a:chunk:0", "doc-b:chunk:0"],
        )

    async def test_comprehensive_search_merges_metadata_candidates(self) -> None:
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

        results = await make_document_search_service(
            documents=documents,
            graph=FakeGraphStore(graph),
            config=DocumentRetrievalConfig(comprehensive_top_k=10),
        ).search(
            RetrievalQuery(
                text="창업",
                request_context=RequestContext(
                    tenant="tenant-1",
                    requested_at="2026-05-17T09:30:00+09:00",
                ),
            ),
            require_comprehensive_search=True,
        )

        self.assertEqual(
            {result.chunk.document_id for result in results},
            {"doc-a", "doc-c"},
        )

    def test_assistant_agents_do_not_depend_on_use_cases(self) -> None:
        project_root = next(
            parent for parent in Path(__file__).resolve().parents if (parent / "src").exists()
        )
        agents_dir = (
            project_root
            / "src"
            / "foldmind_ai_core"
            / "core"
            / "application"
            / "agents"
        )

        for path in agents_dir.glob("*.py"):
            self.assertNotIn("application.use_cases", path.read_text())


if __name__ == "__main__":
    unittest.main()
