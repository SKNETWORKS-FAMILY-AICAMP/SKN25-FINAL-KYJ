from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from foldmind_ai_core.application.workflows.state.plan import WorkflowActionType
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.workflow.tasks import TaskOutputResult, TaskOutputType
from foldmind_ai_core.shared.types import Metadata


class WorkflowArtifactName(StrEnum):
    DOCUMENT_RETRIEVAL = "document_retrieval"
    CANDIDATE_DOCUMENTS = "candidate_documents"
    RELEVANT_DOCUMENTS = "relevant_documents"
    DOCUMENT_SUMMARIES = "document_summaries"
    SYNTHESIZED_REPORT = "synthesized_report"
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


class WorkflowStepStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class WorkflowStepInput:
    query: AIQuery | None = None
    artifact_refs: tuple[WorkflowArtifactName, ...] = ()
    options: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class WorkflowStep:
    action_type: WorkflowActionType
    reason: str = ""
    step_input: WorkflowStepInput = field(default_factory=WorkflowStepInput)


@dataclass(frozen=True, slots=True)
class OutputSpec:
    output_type: TaskOutputType
    output_key: str
    title: str


@dataclass(frozen=True, slots=True)
class StepSpec:
    writes: tuple[WorkflowArtifactName, ...]
    reads: tuple[WorkflowArtifactName, ...] = ()
    output: OutputSpec | None = None


@dataclass(slots=True)
class StepOutcome:
    artifacts: dict[WorkflowArtifactName, object] = field(default_factory=dict)
    output: TaskOutputResult | None = None


@dataclass(slots=True)
class WorkflowExecutionPlan:
    round_index: int = 0
    steps: list[WorkflowStep] = field(default_factory=list)


@dataclass(slots=True)
class WorkflowArtifacts:
    items: dict[WorkflowArtifactName, object] = field(default_factory=dict)

    def read(self, artifact_name: WorkflowArtifactName) -> object | None:
        return self.items.get(artifact_name)

    def write(self, artifact_name: WorkflowArtifactName, value: object) -> None:
        self.items[artifact_name] = value


@dataclass(slots=True)
class WorkflowStepExecution:
    step: WorkflowStep
    round_index: int = 0
    status: WorkflowStepStatus = WorkflowStepStatus.PLANNED
    resolved_query: AIQuery | None = None
    artifacts_read: tuple[WorkflowArtifactName, ...] = ()
    artifacts_written: tuple[WorkflowArtifactName, ...] = ()
    confidence: float | None = None
    error: str | None = None


@dataclass(slots=True)
class WorkflowExecutionTrace:
    rounds: int = 0
    steps: list[WorkflowStepExecution] = field(default_factory=list)
    replans: list[WorkflowExecutionPlan] = field(default_factory=list)


@dataclass(slots=True)
class WorkflowRunResult:
    plan: WorkflowExecutionPlan
    trace: WorkflowExecutionTrace = field(default_factory=WorkflowExecutionTrace)
    artifacts: WorkflowArtifacts = field(default_factory=WorkflowArtifacts)
