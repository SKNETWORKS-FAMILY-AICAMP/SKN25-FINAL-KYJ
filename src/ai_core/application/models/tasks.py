from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypeAlias

from ai_core.application.models.actions import ActionPlan, HostAction
from ai_core.application.models.results import (
    AssistantClarification,
    DocumentRecommendationResult,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from ai_core.common.types import Metadata
from ai_core.common.validation import (
    InvalidInputError,
    require_non_blank,
    require_optional_non_blank,
)


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


class TaskOutputType(StrEnum):
    CLARIFICATION = "clarification"
    DOCUMENT_RECOMMENDATION = "document_recommendation"
    FOLDER_RECOMMENDATION = "folder_recommendation"
    RELATED_RECOMMENDATION = "related_recommendation"
    ANSWER = "answer"
    SUMMARY = "summary"
    DRAFT = "draft"
    IDEAS = "ideas"
    ACTION_PLAN = "action_plan"


TaskOutputResult: TypeAlias = (
    AssistantClarification
    | DocumentRecommendationResult
    | FolderRecommendationResult
    | RelatedRecommendationResult
    | GeneratedTextResult
    | DraftResult
    | ActionPlan
)


@dataclass(slots=True)
class TaskRequest:
    task_id: str
    tenant: str
    request: str
    user_id: str | None = None
    request_id: str | None = None
    conversation_id: str | None = None
    context: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_blank(self.task_id, "task_id")
        require_non_blank(self.tenant, "tenant")
        require_non_blank(self.request, "request")
        require_optional_non_blank(self.user_id, "user_id")
        require_optional_non_blank(self.request_id, "request_id")
        require_optional_non_blank(self.conversation_id, "conversation_id")


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

    def __post_init__(self) -> None:
        require_non_blank(self.event_id, "event_id")
        require_non_blank(self.message, "message")


@dataclass(slots=True)
class TaskOutput:
    output_type: TaskOutputType | str
    result: TaskOutputResult
    output_id: str | None = None
    title: str | None = None
    metadata: Metadata = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            self.output_type = TaskOutputType(self.output_type)
        except ValueError as exc:
            raise InvalidInputError(f"Unsupported output_type: {self.output_type}") from exc
        require_optional_non_blank(self.output_id, "output_id")
        require_optional_non_blank(self.title, "title")
        self._validate_result_matches_output_type()

    def _validate_result_matches_output_type(self) -> None:
        expected_result_types = {
            TaskOutputType.CLARIFICATION: AssistantClarification,
            TaskOutputType.DOCUMENT_RECOMMENDATION: DocumentRecommendationResult,
            TaskOutputType.FOLDER_RECOMMENDATION: FolderRecommendationResult,
            TaskOutputType.RELATED_RECOMMENDATION: RelatedRecommendationResult,
            TaskOutputType.ANSWER: GeneratedTextResult,
            TaskOutputType.SUMMARY: GeneratedTextResult,
            TaskOutputType.DRAFT: DraftResult,
            TaskOutputType.IDEAS: GeneratedTextResult,
            TaskOutputType.ACTION_PLAN: ActionPlan,
        }
        expected_result_type = expected_result_types[self.output_type]
        if not isinstance(self.result, expected_result_type):
            raise InvalidInputError(
                f"{self.output_type} output requires {expected_result_type.__name__} result."
            )


@dataclass(slots=True)
class TaskAnalysis:
    message: str
    outputs: list[TaskOutput] = field(default_factory=list)

    def __post_init__(self) -> None:
        require_non_blank(self.message, "message")


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

    def __post_init__(self) -> None:
        require_non_blank(self.task_id, "task_id")
        require_non_blank(self.tenant, "tenant")
        require_non_blank(self.request, "request")
        require_optional_non_blank(self.error, "error")
        require_optional_non_blank(self.user_id, "user_id")
        require_optional_non_blank(self.request_id, "request_id")
        require_optional_non_blank(self.current_action_id, "current_action_id")
