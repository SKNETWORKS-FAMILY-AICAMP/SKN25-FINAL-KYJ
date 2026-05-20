from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from foldmind_ai_core.core.application.workflows.state.plan import WorkflowActionType
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskOutputResult, TaskOutputType
from foldmind_ai_core.shared.types import JsonObject


class WorkflowArtifactName(StrEnum):
    DOCUMENT_RETRIEVAL = "document_retrieval"
    DOCUMENT_SEARCH_RESULT = "document_search_result"
    SIGNAL_RETRIEVAL = "signal_retrieval"
    SIGNAL_SEARCH_RESULT = "signal_search_result"
    SIGNAL_EVIDENCE = "signal_evidence"
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
    CLARIFICATION = "clarification"


@dataclass(slots=True)
class WorkflowStepInput:
    query: RetrievalQuery | None = None
    artifact_refs: tuple[WorkflowArtifactName, ...] = ()
    options: JsonObject = field(default_factory=dict)


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
class WorkflowExecutionTrace:
    rounds: int = 0
    replans: list[WorkflowExecutionPlan] = field(default_factory=list)
