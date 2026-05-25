from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeVar, cast

from foldmind_ai_core.adapters.outbound.json_model_codec import JsonModelCodec
from foldmind_ai_core.adapters.outbound.workflow_runtime.graph_state import GraphState
from foldmind_ai_core.adapters.outbound.workflow_runtime.workflow_checkpoint import (
    CHECKPOINT_STATE_VERSION,
    WorkflowCheckpointState,
)
from foldmind_ai_core.core.application.ports.outbound.runtime.workflow_runtime import (
    WorkflowArtifactName,
    WorkflowArtifacts,
    WorkflowExecutionPlan,
    WorkflowExecutionTrace,
    WorkflowState,
    WorkflowStep,
    WorkflowStepInput,
)
from foldmind_ai_core.core.application.models.search import (
    RequestContext,
    SearchScope,
    SearchSort,
)
from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.models.generation import (
    AssistantClarification,
    DocumentRecommendation,
    DocumentRecommendationResult,
    DocumentSearchResult,
    DraftResult,
    FolderRecommendation,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.core.application.models.retrieval import (
    FolderRetrievalResult,
    RelatedRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
)
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.core.domain.models.host_actions import (
    ActionPlan,
    CreateDocumentInput,
    CreateDocumentOutput,
    CreateFolderInput,
    CreateFolderOutput,
    HostAction,
    HostActionPolicy,
    HostActionResult,
    LinkDocumentsInput,
    LinkDocumentsOutput,
    MoveDocumentInput,
    MoveDocumentOutput,
    UpdateDocumentInput,
    UpdateDocumentOutput,
)
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskEvent,
    TaskFinalResult,
    TaskInputEntry,
    TaskJob,
    TaskJobResult,
    TaskSnapshot,
)
from foldmind_ai_core.shared.types import JsonObject, JsonValue, Metadata

if TYPE_CHECKING:
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

_TYPE_KEY = "__foldmind_checkpoint_type__"
_VALUE_KEY = "value"

_CHECKPOINT_MODELS = (
    ActionPlan,
    RetrievalQuery,
    AssistantClarification,
    CreateDocumentInput,
    CreateDocumentOutput,
    CreateFolderInput,
    CreateFolderOutput,
    DocumentChunk,
    DocumentRecommendation,
    DocumentRecommendationResult,
    DocumentSearchResult,
    DraftResult,
    FolderRecommendation,
    FolderRecommendationResult,
    FolderRetrievalResult,
    GeneratedTextResult,
    HostAction,
    HostActionPolicy,
    HostActionResult,
    RetrievedDocument,
    SourceFolder,
    LinkDocumentsInput,
    LinkDocumentsOutput,
    MoveDocumentInput,
    MoveDocumentOutput,
    RelatedRecommendationResult,
    RelatedRetrievalResult,
    RequestContext,
    RetrievalResult,
    SearchScope,
    SearchSort,
    TaskAnalysis,
    TaskContext,
    TaskEvent,
    TaskFinalResult,
    TaskInputEntry,
    TaskJob,
    TaskJobResult,
    TaskSnapshot,
    UpdateDocumentInput,
    UpdateDocumentOutput,
    WorkflowArtifacts,
    WorkflowExecutionPlan,
    WorkflowExecutionTrace,
    WorkflowStep,
    WorkflowStepInput,
)


def _post_decode(model_type: type[object], restored: dict[str, object]) -> dict[str, object]:
    if model_type is not WorkflowArtifacts:
        return restored
    items = restored["items"]
    if not isinstance(items, dict):
        raise TypeError("Workflow artifacts checkpoint must contain dictionary items.")
    return {**restored, "items": {_artifact_key(key): item for key, item in items.items()}}


_CODEC = JsonModelCodec(
    models=_CHECKPOINT_MODELS,
    type_key=_TYPE_KEY,
    value_key=_VALUE_KEY,
    localns={
        "JsonValue": JsonValue,
        "JsonObject": JsonObject,
        "Metadata": Metadata,
        "datetime": datetime,
    },
    post_decode=_post_decode,
    label="checkpoint",
)


def langgraph_checkpoint_serializer() -> JsonPlusSerializer:
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    return JsonPlusSerializer()


def workflow_state_to_checkpoint(state: WorkflowState) -> GraphState:
    checkpoint = {
        "state_version": CHECKPOINT_STATE_VERSION,
        **{field.name: checkpoint_value(getattr(state, field.name)) for field in fields(state)},
    }
    return cast(GraphState, _checkpoint_schema(checkpoint))


def workflow_state_from_checkpoint(raw_state: Mapping[str, Any]) -> WorkflowState:
    state = _checkpoint_schema(raw_state)
    if state["state_version"] != CHECKPOINT_STATE_VERSION:
        raise ValueError(
            f"Unsupported workflow checkpoint state version: {state['state_version']}"
        )
    restored: dict[str, Any] = {
        field.name: _CODEC.restore(state[field.name]) for field in fields(WorkflowState)
    }
    return WorkflowState(**restored)


def checkpoint_value(value: object) -> Any:
    return _CODEC.encode(value)


T = TypeVar("T")


def restore_checkpoint_value(value: object, expected_type: type[T]) -> T:
    return _CODEC.restore_typed(value, expected_type)


def _checkpoint_schema(raw_state: Mapping[str, Any]) -> dict[str, Any]:
    fields_to_keep = WorkflowCheckpointState.model_fields
    return WorkflowCheckpointState.model_validate(
        {key: value for key, value in raw_state.items() if key in fields_to_keep}
    ).model_dump(mode="json")


def _artifact_key(key: object) -> object:
    if isinstance(key, WorkflowArtifactName):
        return key
    if isinstance(key, str):
        try:
            return WorkflowArtifactName(key)
        except ValueError:
            return key
    return key
