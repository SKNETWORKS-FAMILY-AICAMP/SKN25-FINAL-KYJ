from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ai_core.schemas.actions import ActionPlan, HostAction
from ai_core.schemas.answer import DraftResult, GeneratedTextResult
from ai_core.schemas.assistant import AssistantClarification
from ai_core.schemas.recommendation import (
    DocumentRecommendationResult,
    FolderRecommendationResult,
    RelatedRecommendationResult,
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
