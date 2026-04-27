from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from ai_core.common.types import Metadata
from ai_core.domain.actions import ActionPlan, HostAction
from ai_core.domain.chunks import RetrievalResult
from ai_core.domain.documents import IndexedDocument
from ai_core.domain.folders import IndexedFolder


@dataclass(slots=True)
class RequestContext:
    tenant: str
    user_id: str | None = None
    request_id: str | None = None
    locale: str | None = None
    timezone: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class SearchScope:
    entity_type: str | None = None
    entity_id: str | None = None
    folder_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata_filter: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class QueryAnchor:
    entity_type: str
    entity_id: str
    source_key: str | None = None


@dataclass(slots=True)
class AIQuery:
    text: str
    scope: SearchScope | None = None
    anchor: QueryAnchor | None = None
    request_context: RequestContext | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(slots=True)
class GeneratedTextResult:
    text: str
    citations: list[RetrievalResult] = field(default_factory=list)


@dataclass(slots=True)
class DraftResult:
    draft: str
    citations: list[RetrievalResult] = field(default_factory=list)


@dataclass(slots=True)
class DocumentRecommendation:
    document: IndexedDocument
    reason: str
    score: float
    evidence: list[RetrievalResult] = field(default_factory=list)


@dataclass(slots=True)
class DocumentRecommendationResult:
    primary: DocumentRecommendation | None = None
    alternatives: list[DocumentRecommendation] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return self.primary.score if self.primary is not None else 0.0


@dataclass(slots=True)
class FolderRecommendation:
    folder: IndexedFolder
    reason: str
    score: float


@dataclass(slots=True)
class FolderRecommendationResult:
    primary: FolderRecommendation
    alternatives: list[FolderRecommendation] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return self.primary.score


@dataclass(slots=True)
class RelatedRecommendationItem:
    target: DocumentRecommendation | FolderRecommendation

    @property
    def score(self) -> float:
        return self.target.score

    @property
    def reason(self) -> str:
        return self.target.reason

    @property
    def document(self) -> DocumentRecommendation | None:
        if isinstance(self.target, DocumentRecommendation):
            return self.target
        return None

    @property
    def folder(self) -> FolderRecommendation | None:
        if isinstance(self.target, FolderRecommendation):
            return self.target
        return None


@dataclass(slots=True)
class RelatedRecommendationResult:
    items: list[RelatedRecommendationItem] = field(default_factory=list)

    @property
    def documents(self) -> list[DocumentRecommendation]:
        return [item.document for item in self.items if item.document is not None]

    @property
    def folders(self) -> list[FolderRecommendation]:
        return [item.folder for item in self.items if item.folder is not None]

    @property
    def confidence(self) -> float:
        return self.items[0].score if self.items else 0.0


class AssistantToolName(StrEnum):
    SEARCH_DOCUMENTS = "search_documents"
    SEARCH_FOLDERS = "search_folders"
    SEARCH_RELATED = "search_related"
    RECOMMEND_DOCUMENTS = "recommend_documents"
    RECOMMEND_FOLDER = "recommend_folder"
    RECOMMEND_RELATED = "recommend_related"
    ANSWER_QUESTION = "answer_question"
    SUMMARIZE_DOCUMENTS = "summarize_documents"
    GENERATE_DRAFT = "generate_draft"
    EXPLORE_IDEAS = "explore_ideas"
    PLAN_ACTIONS = "plan_actions"


class AssistantArtifactName(StrEnum):
    DOCUMENT_RETRIEVAL = "document_retrieval"
    FOLDER_RETRIEVAL = "folder_retrieval"
    RELATED_RETRIEVAL = "related_retrieval"
    DOCUMENT_RECOMMENDATION = "document_recommendation"
    FOLDER_RECOMMENDATION = "folder_recommendation"
    RELATED_RECOMMENDATION = "related_recommendation"
    ANSWER = "answer"
    SUMMARY = "summary"
    DRAFT = "draft"
    IDEAS = "ideas"
    ACTION_PLAN = "action_plan"


class AssistantStepStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class AssistantResponseStatus(StrEnum):
    COMPLETED = "completed"
    CLARIFICATION_REQUIRED = "clarification_required"
    FAILED = "failed"


@dataclass(slots=True)
class AssistantToolInput:
    query: AIQuery | None = None
    artifact_refs: tuple[AssistantArtifactName, ...] = ()
    options: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class AssistantToolCall:
    tool_name: AssistantToolName
    reason: str = ""
    tool_input: AssistantToolInput = field(default_factory=AssistantToolInput)


@dataclass(slots=True)
class AssistantExecutionPlan:
    round_index: int = 0
    steps: list[AssistantToolCall] = field(default_factory=list)


@dataclass(slots=True)
class AssistantArtifacts:
    items: dict[AssistantArtifactName, object] = field(default_factory=dict)

    def read(self, artifact_name: AssistantArtifactName) -> object | None:
        return self.items.get(artifact_name)

    def write(self, artifact_name: AssistantArtifactName, value: object) -> None:
        self.items[artifact_name] = value


@dataclass(slots=True)
class AssistantStepExecution:
    step: AssistantToolCall
    round_index: int = 0
    status: AssistantStepStatus = AssistantStepStatus.PLANNED
    resolved_query: AIQuery | None = None
    artifacts_read: tuple[AssistantArtifactName, ...] = ()
    artifacts_written: tuple[AssistantArtifactName, ...] = ()
    confidence: float | None = None
    error: str | None = None


@dataclass(slots=True)
class AssistantExecutionTrace:
    rounds: int = 0
    steps: list[AssistantStepExecution] = field(default_factory=list)
    replans: list[AssistantExecutionPlan] = field(default_factory=list)


@dataclass(slots=True)
class AssistantClarification:
    question: str
    reason: str


@dataclass(slots=True)
class AssistantResponse:
    response: str
    plan: AssistantExecutionPlan
    status: AssistantResponseStatus = AssistantResponseStatus.COMPLETED
    trace: AssistantExecutionTrace = field(default_factory=AssistantExecutionTrace)
    artifacts: AssistantArtifacts = field(default_factory=AssistantArtifacts)
    clarification: AssistantClarification | None = None


class TaskStatus(StrEnum):
    CLARIFICATION_REQUIRED = "clarification_required"
    AWAITING_DECISION = "awaiting_decision"
    READY_FOR_HOST_ACTION = "ready_for_host_action"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class TaskDecisionType(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class TaskEventType(StrEnum):
    CREATED = "created"
    DECISION_REQUESTED = "decision_requested"
    DECISION_RECEIVED = "decision_received"
    CLARIFICATION_REQUESTED = "clarification_requested"
    HOST_ACTION_READY = "host_action_ready"
    HOST_ACTION_RECORDED = "host_action_recorded"
    HOST_ACTION_RETRY_SCHEDULED = "host_action_retry_scheduled"
    HOST_ACTION_SKIPPED = "host_action_skipped"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass(slots=True)
class TaskRequest:
    task_id: str
    tenant: str
    request: str
    user_id: str | None = None
    request_id: str | None = None
    conversation_id: str | None = None
    context: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class TaskDecision:
    decision_type: TaskDecisionType
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskEvent:
    event_id: str
    event_type: TaskEventType
    message: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskAnalysis:
    response: str
    clarification: AssistantClarification | None = None
    document_recommendation: DocumentRecommendationResult | None = None
    folder_recommendation: FolderRecommendationResult | None = None
    related_recommendation: RelatedRecommendationResult | None = None
    answer: GeneratedTextResult | None = None
    summary: GeneratedTextResult | None = None
    draft: DraftResult | None = None
    ideas: GeneratedTextResult | None = None
    action_plan: ActionPlan | None = None


@dataclass(slots=True)
class TaskSnapshot:
    task_id: str
    tenant: str
    request: str
    status: TaskStatus
    analysis: TaskAnalysis
    host_actions: list[HostAction] = field(default_factory=list)
    error: str | None = None
    user_id: str | None = None
    request_id: str | None = None
    current_action_id: str | None = None
    events: list[TaskEvent] = field(default_factory=list)
    metadata: Metadata = field(default_factory=dict)
