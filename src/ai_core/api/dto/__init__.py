"""Pydantic DTOs for the REST API boundary."""

from ai_core.api.dto.action_inputs import (
    CreateDocumentInputDTO,
    HostActionInputDTO,
    LinkDocumentsInputDTO,
    MoveDocumentInputDTO,
    UpdateDocumentInputDTO,
)
from ai_core.api.dto.action_outputs import (
    CreateDocumentOutputDTO,
    HostActionResultOutputDTO,
    LinkDocumentsOutputDTO,
    MoveDocumentOutputDTO,
    UpdateDocumentOutputDTO,
)
from ai_core.api.dto.action_plans import (
    ActionPlanDTO,
    HostActionDTO,
    HostActionPolicyDTO,
)
from ai_core.api.dto.action_results import (
    HostActionResultDTO,
    RecordHostActionResultRequest,
    RecordHostActionResultResponse,
)
from ai_core.api.dto.base import APIBaseDTO
from ai_core.api.dto.documents import IndexedDocumentDTO, IndexedFolderDTO, SourceDocumentDTO
from ai_core.api.dto.generation import (
    AssistantClarificationDTO,
    DraftResultDTO,
    GeneratedTextResponse,
)
from ai_core.api.dto.indexing import (
    DeleteDocumentIndexRequest,
    DeleteDocumentIndexResponse,
    IndexDocumentRequest,
    IndexDocumentResponse,
)
from ai_core.api.dto.outputs import (
    ActionPlanOutputDTO,
    AnswerOutputDTO,
    ClarificationOutputDTO,
    DocumentRecommendationOutputDTO,
    DraftOutputDTO,
    FolderRecommendationOutputDTO,
    IdeasOutputDTO,
    RelatedRecommendationOutputDTO,
    SummaryOutputDTO,
    TaskOutputDTO,
    TaskOutputMetaDTO,
)
from ai_core.api.dto.queries import (
    AIQueryDTO,
    QueryAnchorDTO,
    RequestContextDTO,
    SearchScopeDTO,
)
from ai_core.api.dto.recommendations import (
    DocumentRecommendationDTO,
    DocumentRecommendationResultDTO,
    FolderRecommendationDTO,
    FolderRecommendationResultDTO,
    RecommendFolderRequest,
    RecommendFolderResponse,
    RelatedRecommendationItemDTO,
    RelatedRecommendationResultDTO,
)
from ai_core.api.dto.retrieval import (
    AnswerQuestionRequest,
    RetrievalResultDTO,
    SearchDocumentsRequest,
    SearchDocumentsResponse,
)
from ai_core.api.dto.tasks import (
    CreateTaskRequest,
    TaskAnalysisDTO,
    TaskEventDTO,
    TaskSnapshotDTO,
    TaskSnapshotResponse,
)

__all__ = [
    "AIQueryDTO",
    "APIBaseDTO",
    "ActionPlanDTO",
    "ActionPlanOutputDTO",
    "AnswerOutputDTO",
    "AnswerQuestionRequest",
    "AssistantClarificationDTO",
    "ClarificationOutputDTO",
    "CreateDocumentInputDTO",
    "CreateDocumentOutputDTO",
    "CreateTaskRequest",
    "DeleteDocumentIndexRequest",
    "DeleteDocumentIndexResponse",
    "DocumentRecommendationDTO",
    "DocumentRecommendationOutputDTO",
    "DocumentRecommendationResultDTO",
    "DraftOutputDTO",
    "DraftResultDTO",
    "FolderRecommendationDTO",
    "FolderRecommendationOutputDTO",
    "FolderRecommendationResultDTO",
    "GeneratedTextResponse",
    "HostActionDTO",
    "HostActionInputDTO",
    "HostActionPolicyDTO",
    "HostActionResultDTO",
    "HostActionResultOutputDTO",
    "IdeasOutputDTO",
    "IndexedDocumentDTO",
    "IndexedFolderDTO",
    "IndexDocumentRequest",
    "IndexDocumentResponse",
    "LinkDocumentsInputDTO",
    "LinkDocumentsOutputDTO",
    "MoveDocumentInputDTO",
    "MoveDocumentOutputDTO",
    "QueryAnchorDTO",
    "RecommendFolderRequest",
    "RecommendFolderResponse",
    "RecordHostActionResultRequest",
    "RecordHostActionResultResponse",
    "RelatedRecommendationItemDTO",
    "RelatedRecommendationOutputDTO",
    "RelatedRecommendationResultDTO",
    "RequestContextDTO",
    "RetrievalResultDTO",
    "SearchDocumentsRequest",
    "SearchDocumentsResponse",
    "SearchScopeDTO",
    "SourceDocumentDTO",
    "SummaryOutputDTO",
    "TaskAnalysisDTO",
    "TaskEventDTO",
    "TaskOutputDTO",
    "TaskOutputMetaDTO",
    "TaskSnapshotDTO",
    "TaskSnapshotResponse",
    "UpdateDocumentInputDTO",
    "UpdateDocumentOutputDTO",
]
