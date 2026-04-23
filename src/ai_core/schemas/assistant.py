from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from ai_core.common.types import Metadata
from ai_core.schemas.query import AIQuery


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
