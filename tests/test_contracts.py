from __future__ import annotations

import unittest
from pathlib import Path
from typing import get_args, get_type_hints

from pydantic import BaseModel, ValidationError

from ai_core.common import Metadata, Vector
from ai_core.agents.search_agent import (
    HybridSearchConfig,
    SearchMode,
    SearchAgent,
    reciprocal_rank_fusion,
)
from ai_core.application.use_cases.hybrid_search import HybridSearchUseCase
from ai_core.application.models.actions import (
    ActionPlan,
    CreateDocumentInput,
    CreateDocumentOutput,
    HostAction,
    HostActionInput,
    HostActionResult,
    HostActionResultType,
    HostActionType,
    MoveDocumentInput,
)
from ai_core.application.models.llm import LLMMessage
from ai_core.application.models.queries import AIQuery, RequestContext, SearchScope
from ai_core.application.models.results import (
    AssistantResponse,
    AssistantResponseStatus,
    GeneratedTextResult,
)
from ai_core.application.models.retrieval import RetrievalResult
from ai_core.application.models.tasks import (
    TaskAnalysis,
    TaskEvent,
    TaskOutput,
    TaskOutputType,
    TaskRequest,
    TaskSnapshot,
    TaskStatus,
)
from ai_core.domain.chunks import DocumentChunk
from ai_core.common.validation import InvalidInputError
from ai_core.workflows.models.assistant import AssistantExecutionPlan, AssistantRunResult
from ai_core.application.ports import TaskStore
from ai_core.api.dto import (
    APIBaseDTO,
    ActionPlanDTO,
    AIQueryDTO,
    AnswerQuestionRequest,
    AssistantClarificationDTO,
    CreateDocumentInputDTO,
    CreateDocumentOutputDTO,
    DocumentRecommendationDTO,
    DocumentRecommendationResultDTO,
    DraftResultDTO,
    FolderRecommendationDTO,
    FolderRecommendationResultDTO,
    HostActionDTO,
    HostActionInputDTO,
    HostActionResultDTO,
    HostActionResultOutputDTO,
    IndexedDocumentDTO,
    IndexedFolderDTO,
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
    SourceDocumentDTO,
    TaskAnalysisDTO,
    TaskSnapshotDTO,
    TaskSnapshotResponse,
    UpdateDocumentInputDTO,
    UpdateDocumentOutputDTO,
)
from ai_core.domain.documents import SourceDocument


class InMemoryTaskStore:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], TaskSnapshot] = {}

    def create(self, request: TaskRequest, snapshot: TaskSnapshot) -> None:
        self.items[(request.tenant, request.task_id)] = snapshot

    def get(self, *, tenant: str, task_id: str) -> TaskSnapshot | None:
        return self.items.get((tenant, task_id))

    def save(self, snapshot: TaskSnapshot) -> None:
        self.items[(snapshot.tenant, snapshot.task_id)] = snapshot

    def append_event(self, *, tenant: str, task_id: str, event: TaskEvent) -> None:
        snapshot = self.items[(tenant, task_id)]
        snapshot.events.append(event)


class FakeEmbeddingProvider:
    def embed_texts(self, texts: list[str]) -> list[Vector]:
        return [[float(len(text))] for text in texts]


class FakeDocumentVectorStore:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.upserted: list[DocumentChunk] = []
        self.deleted: list[tuple[str, str, str]] = []

    def upsert(self, chunks: list[DocumentChunk], vectors: list[Vector]) -> None:
        self.upserted.extend(chunks)

    def delete(self, *, tenant: str, entity_type: str, entity_id: str) -> None:
        self.deleted.append((tenant, entity_type, entity_id))

    def similarity_search(
        self,
        *,
        tenant: str,
        query_vector: Vector,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return self.results[:top_k]


class FakeKeywordSearchStore:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.upserted: list[DocumentChunk] = []
        self.deleted: list[tuple[str, str, str]] = []

    def upsert(self, chunks: list[DocumentChunk]) -> None:
        self.upserted.extend(chunks)

    def delete(self, *, tenant: str, entity_type: str, entity_id: str) -> None:
        self.deleted.append((tenant, entity_type, entity_id))

    def keyword_search(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        scope: SearchScope | None = None,
    ) -> list[RetrievalResult]:
        return self.results[:top_k]


def make_chunk(chunk_id: str, text: str = "text") -> DocumentChunk:
    return DocumentChunk(
        tenant="tenant-1",
        entity_type="document",
        entity_id=chunk_id.split("-")[0],
        version="v1",
        chunk_id=chunk_id,
        text=text,
        chunk_index=0,
        start_offset=0,
        end_offset=len(text),
    )


class ContractTests(unittest.TestCase):
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
                entity_type="document",
                entity_id="doc-1",
                target_folder_id="folder-1",
            ),
        )

        self.assertEqual(action.action_type, HostActionType.MOVE_DOCUMENT)
        self.assertIsInstance(action.input, MoveDocumentInput)

        dto = HostActionDTO.from_model(action)

        self.assertEqual(dto.action_type, HostActionType.MOVE_DOCUMENT)
        self.assertIsInstance(dto.input, MoveDocumentInputDTO)
        self.assertEqual(dto.input.target_folder_id, "folder-1")

    def test_host_action_rejects_mismatched_payload(self) -> None:
        with self.assertRaises(InvalidInputError):
            HostAction(
                action_type=HostActionType.MOVE_DOCUMENT,
                summary="Move the document.",
                input=None,  # type: ignore[arg-type]
            )

        with self.assertRaises(InvalidInputError):
            HostAction(
                action_type=HostActionType.MOVE_DOCUMENT,
                summary="Move the document.",
                input=CreateDocumentInput(title="Title", body="Body"),
            )

        with self.assertRaises(InvalidInputError):
            HostAction(
                action_type="unsupported_action",
                summary="Run an unsupported action.",
                input=CreateDocumentInput(title="Title", body="Body"),
            )

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
        context = RequestContext(tenant="tenant-1", user_id="user-1")
        scope = SearchScope(entity_type="document", folder_ids=("folder-1",))

        self.assertEqual(context.tenant, "tenant-1")
        self.assertEqual(scope.folder_ids, ("folder-1",))

    def test_task_snapshot_keeps_workflow_context(self) -> None:
        request = TaskRequest(
            task_id="task-1",
            tenant="tenant-1",
            request="Summarize related meeting notes.",
            user_id="user-1",
        )
        snapshot = TaskSnapshot(
            task_id=request.task_id,
            tenant=request.tenant,
            request=request.request,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
            user_id=request.user_id,
        )

        self.assertEqual(snapshot.user_id, "user-1")
        self.assertEqual(snapshot.status, TaskStatus.COMPLETED)

    def test_application_ports_are_structural(self) -> None:
        store: TaskStore = InMemoryTaskStore()
        request = TaskRequest(task_id="task-1", tenant="tenant-1", request="Test")
        snapshot = TaskSnapshot(
            task_id=request.task_id,
            tenant=request.tenant,
            request=request.request,
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
        )

        store.create(request, snapshot)

        self.assertIs(store.get(tenant="tenant-1", task_id="task-1"), snapshot)

    def test_indexing_dto_maps_to_domain_without_holding_domain_model(self) -> None:
        request = IndexDocumentRequest(
            document=SourceDocumentDTO(
                tenant="tenant-1",
                entity_type="document",
                entity_id="doc-1",
                version="v1",
                title="Title",
                body="Body",
            )
        )

        document = request.to_model()

        self.assertIsInstance(request.document, SourceDocumentDTO)
        self.assertIsInstance(document, SourceDocument)
        self.assertEqual(document.document_key, "tenant-1:document:doc-1")

    def test_task_response_dto_maps_from_model_without_exposing_internal_model(self) -> None:
        snapshot = TaskSnapshot(
            task_id="task-1",
            tenant="tenant-1",
            request="Test",
            status=TaskStatus.COMPLETED,
            analysis=TaskAnalysis(message="Done."),
        )

        response = TaskSnapshotResponse.from_model(snapshot)

        self.assertEqual(response.task.status, TaskStatus.COMPLETED)
        self.assertEqual(response.task.analysis.message, "Done.")

    def test_action_result_dto_maps_to_model(self) -> None:
        result = HostActionResultDTO(
            action_id="action-1",
            outcome="failed",
            error="Execution failed.",
        ).to_model()

        self.assertIsInstance(result, HostActionResult)
        self.assertEqual(result.outcome, HostActionResultType.FAILED)
        self.assertIsNone(result.output)

        created = HostActionResultDTO(
            action_id="action-2",
            action_type=HostActionType.CREATE_DOCUMENT,
            outcome=HostActionResultType.SUCCEEDED,
            output=CreateDocumentOutputDTO(created_entity_id="doc-1"),
        ).to_model()

        self.assertEqual(created.action_type, "create_document")
        self.assertIsInstance(created.output, CreateDocumentOutput)
        self.assertEqual(created.output.created_entity_id, "doc-1")

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
                action_id="action-1",
                action_type=HostActionType.MOVE_DOCUMENT,
                outcome=HostActionResultType.SUCCEEDED,
                output=CreateDocumentOutputDTO(created_entity_id="doc-1"),
            )

    def test_api_dtos_defer_blank_validation_to_application_models(self) -> None:
        document = SourceDocumentDTO(
            tenant="tenant-1",
            entity_type="document",
            entity_id="",
            version="v1",
            title="Title",
            body="Body",
        )
        query = AIQueryDTO(text=" ", request_context={"tenant": "tenant-1"})
        result = HostActionResultDTO(
            action_id="",
            outcome=HostActionResultType.SUCCEEDED,
        )

        with self.assertRaises(InvalidInputError):
            document.to_model()

        with self.assertRaises(InvalidInputError):
            query.to_model()

        with self.assertRaises(InvalidInputError):
            result.to_model()

    def test_application_models_reject_blank_identifiers(self) -> None:
        with self.assertRaises(InvalidInputError):
            RequestContext(tenant=" ")

        with self.assertRaises(InvalidInputError):
            SourceDocument(
                tenant="tenant-1",
                entity_type="document",
                entity_id="",
                version="v1",
                title="Title",
                body="Body",
            )

        with self.assertRaises(InvalidInputError):
            CreateDocumentInput(title="Title", body="Body", folder_id=" ")

        with self.assertRaises(InvalidInputError):
            MoveDocumentInput(
                entity_type="document",
                entity_id="",
                target_folder_id="folder-1",
            )

        with self.assertRaises(InvalidInputError):
            MoveDocumentInput(
                entity_type="document",
                entity_id="doc-1",
                target_folder_id=" ",
            )

        with self.assertRaises(InvalidInputError):
            CreateDocumentOutput(created_entity_id="")

        with self.assertRaises(InvalidInputError):
            HostActionResult(
                action_id="",
                outcome=HostActionResultType.SUCCEEDED,
            )

        with self.assertRaises(InvalidInputError):
            TaskRequest(
                task_id=" ",
                tenant="tenant-1",
                request="Summarize notes.",
            )

    def test_application_models_reject_blank_natural_language_requests(self) -> None:
        with self.assertRaises(InvalidInputError):
            AIQuery(
                text="   ",
                request_context=RequestContext(tenant="tenant-1"),
            )

        with self.assertRaises(InvalidInputError):
            TaskRequest(
                task_id="task-1",
                tenant="tenant-1",
                request="",
            )

    def test_api_dtos_do_not_use_domain_models_as_fields(self) -> None:
        dto_field_types = {
            get_type_hints(dto)[field_name]
            for dto in (
                AnswerQuestionRequest,
                ActionPlanDTO,
                AssistantClarificationDTO,
                CreateDocumentInputDTO,
                CreateDocumentOutputDTO,
                DocumentRecommendationDTO,
                DocumentRecommendationResultDTO,
                DraftResultDTO,
                FolderRecommendationDTO,
                FolderRecommendationResultDTO,
                HostActionDTO,
                IndexedDocumentDTO,
                IndexedFolderDTO,
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
            task_id="task-1",
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

    def test_task_output_rejects_mismatched_result(self) -> None:
        with self.assertRaises(InvalidInputError):
            TaskOutput(
                output_type=TaskOutputType.ANSWER,
                result=ActionPlan(summary="Plan.", steps=["create draft"]),
            )

        with self.assertRaises(InvalidInputError):
            TaskOutput(
                output_type="unsupported_output",
                result=GeneratedTextResult(text="Answer."),
            )

    def test_models_are_split_by_layer_concern(self) -> None:
        self.assertEqual(AIQuery.__module__, "ai_core.application.models.queries")
        self.assertEqual(RetrievalResult.__module__, "ai_core.application.models.retrieval")
        self.assertEqual(LLMMessage.__module__, "ai_core.application.models.llm")
        self.assertEqual(GeneratedTextResult.__module__, "ai_core.application.models.results")
        self.assertEqual(AssistantResponse.__module__, "ai_core.application.models.results")
        self.assertEqual(AssistantResponseStatus.__module__, "ai_core.application.models.results")
        self.assertEqual(AssistantRunResult.__module__, "ai_core.workflows.models.assistant")
        self.assertEqual(TaskSnapshot.__module__, "ai_core.application.models.tasks")

    def test_assistant_response_does_not_expose_workflow_internals(self) -> None:
        response = AssistantResponse(response="Done.")
        run_result = AssistantRunResult(plan=AssistantExecutionPlan())

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

    def test_hybrid_search_use_case_uses_rrf(self) -> None:
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

        results = HybridSearchUseCase(
            search=SearchAgent(
                embeddings=FakeEmbeddingProvider(),
                documents=FakeDocumentVectorStore(dense),
                keywords=FakeKeywordSearchStore(keyword),
                config=HybridSearchConfig(
                    mode=SearchMode.HYBRID,
                    top_k=2,
                    dense_top_k=2,
                    keyword_top_k=2,
                ),
            )
        ).execute(AIQuery(text="meeting notes", request_context=RequestContext(tenant="tenant-1")))

        self.assertEqual(
            [result.chunk.chunk_id for result in results],
            ["doc-b:chunk:0", "doc-a:chunk:0"],
        )

    def test_search_agent_uses_hybrid_when_keyword_store_is_available(self) -> None:
        chunk_a = make_chunk("doc-a:chunk:0")
        chunk_b = make_chunk("doc-b:chunk:0")

        results = SearchAgent(
            embeddings=FakeEmbeddingProvider(),
            documents=FakeDocumentVectorStore(
                [
                    RetrievalResult(chunk=chunk_a, score=0.95),
                    RetrievalResult(chunk=chunk_b, score=0.90),
                ]
            ),
            keywords=FakeKeywordSearchStore(
                [
                    RetrievalResult(chunk=chunk_b, score=12.0),
                ]
            ),
            config=HybridSearchConfig(mode=SearchMode.HYBRID, top_k=1),
        ).search_documents(
            AIQuery(text="meeting notes", request_context=RequestContext(tenant="tenant-1"))
        )

        self.assertEqual(results[0].chunk.chunk_id, "doc-b:chunk:0")

    def test_agents_do_not_depend_on_use_cases(self) -> None:
        agents_dir = Path(__file__).parents[1] / "src" / "ai_core" / "agents"

        for path in agents_dir.glob("*.py"):
            self.assertNotIn("application.use_cases", path.read_text())


if __name__ == "__main__":
    unittest.main()
