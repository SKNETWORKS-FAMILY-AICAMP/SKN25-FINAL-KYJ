from __future__ import annotations

from typing import Any, TypeVar

from foldmind_ai_core.adapters.outbound.json_model_codec import JsonModelCodec
from foldmind_ai_core.core.domain.models.generation.results import (
    AssistantClarification,
    DocumentRecommendation,
    DocumentRecommendationResult,
    DocumentSearchItem,
    DocumentSearchResult,
    DraftResult,
    FolderRecommendation,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationItem,
    RelatedRecommendationResult,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.retrieval.results import (
    FolderRetrievalResult,
    RelatedRetrievalItem,
    RelatedRetrievalResult,
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
    HostActionPolicy,
    HostActionResult,
    LinkDocumentsInput,
    LinkDocumentsOutput,
    MoveDocumentInput,
    MoveDocumentOutput,
    UpdateDocumentInput,
    UpdateDocumentOutput,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAnalysis,
    TaskAppendInput,
    TaskContext,
    TaskCreationInput,
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

_DOMAIN_MODELS = (
    ActionPlan,
    AssistantClarification,
    CreateDocumentInput,
    CreateDocumentOutput,
    CreateFolderInput,
    CreateFolderOutput,
    DocumentChunk,
    DocumentRecommendation,
    DocumentRecommendationResult,
    DocumentSearchItem,
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
    RetrievedFolder,
    LinkDocumentsInput,
    LinkDocumentsOutput,
    MoveDocumentInput,
    MoveDocumentOutput,
    RelatedRecommendationItem,
    RelatedRecommendationResult,
    RelatedRetrievalItem,
    RelatedRetrievalResult,
    RetrievalResult,
    TaskAnalysis,
    TaskAppendInput,
    TaskContext,
    TaskCreationInput,
    TaskEvent,
    TaskFinalResult,
    TaskInputEntry,
    TaskJob,
    TaskJobResult,
    TaskSnapshot,
    UpdateDocumentInput,
    UpdateDocumentOutput,
)

_DOMAIN_MODEL_CODEC = JsonModelCodec(
    models=_DOMAIN_MODELS,
    type_key=_TYPE_KEY,
    value_key=_VALUE_KEY,
    localns={
        "JsonValue": JsonValue,
        "JsonObject": JsonObject,
        "Metadata": Metadata,
    },
    label="domain model",
)


def domain_model_json(value: object) -> Any:
    return _DOMAIN_MODEL_CODEC.encode(value)


T = TypeVar("T")


def restore_domain_model_json(value: object, expected_type: type[T]) -> T:
    return _DOMAIN_MODEL_CODEC.restore_typed(value, expected_type)
