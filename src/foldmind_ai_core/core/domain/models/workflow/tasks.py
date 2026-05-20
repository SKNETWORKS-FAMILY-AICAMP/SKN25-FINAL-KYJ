from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TypeAlias

from foldmind_ai_core.core.domain.models.generation.results import (
    AssistantClarification,
    DocumentRecommendationResult,
    DocumentSearchResult,
    DraftResult,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationResult,
)
from foldmind_ai_core.core.domain.models.workflow.actions import ActionPlan, HostAction
from foldmind_ai_core.shared.internal_ids import new_internal_id
from foldmind_ai_core.shared.types import JsonObject, Metadata


class TaskStatus(StrEnum):
    CLARIFICATION_REQUIRED = "clarification_required"
    AWAITING_DECISION = "awaiting_decision"
    READY_FOR_HOST_ACTION = "ready_for_host_action"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


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


class TaskInputStatus(StrEnum):
    ACTIVE = "active"
    REMOVED = "removed"


class TaskJobStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskOutputType(StrEnum):
    CLARIFICATION = "clarification"
    DOCUMENT_RECOMMENDATION = "document_recommendation"
    DOCUMENT_SEARCH_RESULT = "document_search_result"
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
    | DocumentSearchResult
    | FolderRecommendationResult
    | RelatedRecommendationResult
    | GeneratedTextResult
    | DraftResult
    | ActionPlan
)


@dataclass(slots=True)
class TaskContext:
    requested_at: str
    document_id: str | None = None
    folder_id: str | None = None


@dataclass(slots=True)
class TaskCreationInput:
    tenant: str
    request: str
    context: TaskContext
    task_input_id: str = field(default_factory=new_internal_id)


@dataclass(slots=True)
class TaskAppendInput:
    task_id: str
    request: str
    context: TaskContext
    task_input_id: str = field(default_factory=new_internal_id)


@dataclass(slots=True)
class TaskInputEntry:
    task_input_id: str
    task_id: str
    input_text: str
    context: TaskContext
    position: int
    status: TaskInputStatus = TaskInputStatus.ACTIVE


@dataclass(slots=True)
class TaskEvent:
    event_type: TaskEventType
    message: str
    data: JsonObject = field(default_factory=dict)
    event_id: str = field(default_factory=new_internal_id)
    job_id: str | None = None


@dataclass(slots=True)
class TaskJobResult:
    result_type: str
    result: TaskOutputResult | JsonObject
    summary: JsonObject = field(default_factory=dict)
    job_result_id: str = field(default_factory=new_internal_id)
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class TaskJob:
    job_type: str
    round_index: int
    position: int
    job_id: str = field(default_factory=new_internal_id)
    status: TaskJobStatus = TaskJobStatus.PLANNED
    reason: str = ""
    input: JsonObject = field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    metadata: Metadata = field(default_factory=dict)
    results: list[TaskJobResult] = field(default_factory=list)


@dataclass(slots=True)
class TaskFinalResult:
    result_type: TaskOutputType
    result: TaskOutputResult
    title: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class TaskAnalysis:
    message: str


@dataclass(slots=True)
class TaskSnapshot:
    task_id: str
    tenant: str
    request: str
    context: TaskContext
    status: TaskStatus
    analysis: TaskAnalysis
    inputs: list[TaskInputEntry] = field(default_factory=list)
    jobs: list[TaskJob] = field(default_factory=list)
    result: TaskFinalResult | None = None
    host_actions: list[HostAction] = field(default_factory=list)
    error: str | None = None
    current_action_id: str | None = None
    events: list[TaskEvent] = field(default_factory=list)
    metadata: Metadata = field(default_factory=dict)
