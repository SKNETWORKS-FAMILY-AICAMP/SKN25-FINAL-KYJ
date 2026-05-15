from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypeAlias

from foldmind_ai_core.domain.generation.results import (
    AssistantClarification,
    DocumentRecommendationResult,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.domain.workflow.actions import ActionPlan, HostAction
from foldmind_ai_core.shared.internal_ids import new_internal_id
from foldmind_ai_core.shared.types import Metadata


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


class TaskRequestStatus(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"


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
class TaskCreationRequest:
    tenant: str
    request: str
    task_request_id: str = field(default_factory=new_internal_id)


@dataclass(slots=True)
class TaskAppendRequest:
    task_id: str
    request: str
    task_request_id: str = field(default_factory=new_internal_id)


@dataclass(slots=True)
class TaskRequestEntry:
    task_request_id: str
    task_id: str
    request: str
    position: int
    status: TaskRequestStatus = TaskRequestStatus.ACTIVE


@dataclass(slots=True)
class TaskDecision:
    decision_type: TaskDecisionType
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TaskEvent:
    event_type: TaskEventType
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=new_internal_id)


@dataclass(slots=True)
class TaskOutput:
    output_type: TaskOutputType | str
    result: TaskOutputResult
    output_id: str = field(default_factory=new_internal_id)
    title: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class TaskAnalysis:
    message: str
    outputs: list[TaskOutput] = field(default_factory=list)


@dataclass(slots=True)
class TaskSnapshot:
    task_id: str
    tenant: str
    request: str
    status: TaskStatus
    analysis: TaskAnalysis
    requests: list[TaskRequestEntry] = field(default_factory=list)
    host_actions: list[HostAction] = field(default_factory=list)
    error: str | None = None
    current_action_id: str | None = None
    events: list[TaskEvent] = field(default_factory=list)
    metadata: Metadata = field(default_factory=dict)
