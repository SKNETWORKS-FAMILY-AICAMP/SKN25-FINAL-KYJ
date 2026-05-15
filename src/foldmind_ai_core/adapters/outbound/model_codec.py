from __future__ import annotations

from typing import Any, TypeVar

from foldmind_ai_core.adapters.outbound.json_model_codec import JsonModelCodec
from foldmind_ai_core.domain.generation.results import (
    AssistantClarification,
    DocumentRecommendation,
    DocumentRecommendationResult,
    DraftResult,
    FolderRecommendation,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationItem,
    RelatedRecommendationResult,
)
from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.retrieval.results import (
    FolderRetrievalResult,
    RelatedRetrievalItem,
    RelatedRetrievalResult,
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
    HostActionPolicy,
    HostActionResult,
    LinkDocumentsInput,
    LinkDocumentsOutput,
    MoveDocumentInput,
    MoveDocumentOutput,
    UpdateDocumentInput,
    UpdateDocumentOutput,
)
from foldmind_ai_core.domain.workflow.tasks import (
    TaskAnalysis,
    TaskAppendRequest,
    TaskCreationRequest,
    TaskEvent,
    TaskOutput,
    TaskSnapshot,
)
from foldmind_ai_core.shared.types import JsonValue, Metadata

_TYPE_KEY = "__foldmind_model_type__"
_VALUE_KEY = "value"

_MODELS = (
    ActionPlan,
    AssistantClarification,
    CreateDocumentInput,
    CreateDocumentOutput,
    CreateFolderInput,
    CreateFolderOutput,
    DocumentChunk,
    DocumentRecommendation,
    DocumentRecommendationResult,
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
    TaskAppendRequest,
    TaskCreationRequest,
    TaskEvent,
    TaskOutput,
    TaskSnapshot,
    UpdateDocumentInput,
    UpdateDocumentOutput,
)

_CODEC = JsonModelCodec(
    models=_MODELS,
    type_key=_TYPE_KEY,
    value_key=_VALUE_KEY,
    localns={
        "JsonValue": JsonValue,
        "Metadata": Metadata,
    },
    label="model",
)


def model_value(value: object) -> Any:
    return _CODEC.encode(value)


T = TypeVar("T")


def restore_model_value(value: object, expected_type: type[T]) -> T:
    return _CODEC.restore_typed(value, expected_type)
