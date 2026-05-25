from __future__ import annotations

from typing import Any, TypeVar

from foldmind_ai_core.adapters.outbound.json_model_codec import JsonModelCodec
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

_TYPE_KEY = "__foldmind_model_type__"
_VALUE_KEY = "value"

_WORKFLOW_MODELS = (
    ActionPlan,
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
    RetrievalResult,
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
)

_WORKFLOW_MODEL_CODEC = JsonModelCodec(
    models=_WORKFLOW_MODELS,
    type_key=_TYPE_KEY,
    value_key=_VALUE_KEY,
    localns={
        "JsonValue": JsonValue,
        "JsonObject": JsonObject,
        "Metadata": Metadata,
    },
    label="workflow model",
)


def workflow_model_json(value: object) -> Any:
    return _WORKFLOW_MODEL_CODEC.encode(value)


T = TypeVar("T")


def restore_workflow_model_json(value: object, expected_type: type[T]) -> T:
    return _WORKFLOW_MODEL_CODEC.restore_typed(value, expected_type)
