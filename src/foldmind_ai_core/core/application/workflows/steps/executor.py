from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from inspect import isawaitable
from typing import Protocol

from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.services.retrieval.document_search_service import (
    DocumentSearchService,
)
from foldmind_ai_core.core.application.services.retrieval.folder_search_service import (
    FolderSearchService,
)
from foldmind_ai_core.core.application.services.retrieval.signal_search_service import (
    SignalSearchService,
)
from foldmind_ai_core.core.application.workflows.artifacts.registry import (
    WorkflowArtifactRegistry,
)
from foldmind_ai_core.core.application.workflows.host_actions.builder import HostActionBuilder
from foldmind_ai_core.core.application.workflows.host_actions.result_service import (
    HostActionResultService,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    StepOutcome,
)
from foldmind_ai_core.core.application.workflows.state.plan import WorkflowActionType
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.workflows.steps.generation import (
    answer_question,
    explore_ideas,
    generate_draft,
    request_clarification,
    summarize_documents,
    synthesize_report,
)
from foldmind_ai_core.core.application.workflows.steps.host_action import plan_host_actions
from foldmind_ai_core.core.application.workflows.steps.recommendation import (
    recommend_documents,
    recommend_folder,
    recommend_related,
)
from foldmind_ai_core.core.application.workflows.steps.retrieval import (
    analyze_documents,
    classify_documents,
    expand_signal_evidence,
    extract_on_demand_signals,
    find_documents,
    find_folders,
    find_related,
    find_signals,
    present_documents,
    present_signals,
    synthesize_signals,
)
from foldmind_ai_core.core.application.workflows.steps.specs import STEP_SPECS
from foldmind_ai_core.core.application.models.generation import GeneratedTextResult
from foldmind_ai_core.core.application.models.retrieval import RetrievalResult
from foldmind_ai_core.core.domain.models.tasks import TaskJob
from foldmind_ai_core.shared.types import JsonObject

from ...services.recommendation.folder_recommendation_service import (
    FolderRecommendationService,
)
from ...services.recommendation.folder_recommendation_source_resolver import (
    FolderRecommendationSourceResolver,
)


class ContextGenerator(Protocol):
    async def generate(
        self,
        *,
        prompt_name: str,
        instruction: str,
        citations: list[RetrievalResult],
    ) -> GeneratedTextResult:
        ...


@dataclass(slots=True)
class WorkflowStepExecutor:
    document_search: DocumentSearchService
    signal_search: SignalSearchService
    folder_search: FolderSearchService
    folder_recommendation: FolderRecommendationService
    folder_recommendation_sources: FolderRecommendationSourceResolver
    context_generator: ContextGenerator
    host_action_builder: HostActionBuilder
    artifacts: WorkflowArtifactRegistry
    host_action_results: HostActionResultService
    _step_functions: dict[WorkflowActionType, WorkflowStepFunction] = field(
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        self._step_functions = {
            WorkflowActionType.FIND_DOCUMENTS: find_documents,
            WorkflowActionType.PRESENT_DOCUMENTS: present_documents,
            WorkflowActionType.FIND_SIGNALS: find_signals,
            WorkflowActionType.PRESENT_SIGNALS: present_signals,
            WorkflowActionType.EXPAND_SIGNAL_EVIDENCE: expand_signal_evidence,
            WorkflowActionType.SYNTHESIZE_SIGNALS: synthesize_signals,
            WorkflowActionType.EXTRACT_ON_DEMAND_SIGNALS: extract_on_demand_signals,
            WorkflowActionType.FIND_FOLDERS: find_folders,
            WorkflowActionType.FIND_RELATED: find_related,
            WorkflowActionType.CLASSIFY_DOCUMENTS: classify_documents,
            WorkflowActionType.ANALYZE_DOCUMENTS: analyze_documents,
            WorkflowActionType.SYNTHESIZE_REPORT: synthesize_report,
            WorkflowActionType.RECOMMEND_DOCUMENTS: recommend_documents,
            WorkflowActionType.RECOMMEND_FOLDER: recommend_folder,
            WorkflowActionType.RECOMMEND_RELATED: recommend_related,
            WorkflowActionType.ANSWER_QUESTION: answer_question,
            WorkflowActionType.SUMMARIZE_DOCUMENTS: summarize_documents,
            WorkflowActionType.GENERATE_DRAFT: generate_draft,
            WorkflowActionType.EXPLORE_IDEAS: explore_ideas,
            WorkflowActionType.PLAN_HOST_ACTIONS: plan_host_actions,
            WorkflowActionType.REQUEST_CLARIFICATION: request_clarification,
        }

    async def execute(
        self,
        state: WorkflowState,
        action_type: WorkflowActionType,
        step_query: RetrievalQuery,
        options: JsonObject,
        job: TaskJob,
    ) -> None:
        spec = STEP_SPECS.get(action_type)
        step_function = self._step_functions.get(action_type)
        if spec is None or step_function is None:
            raise RuntimeError(f"Unsupported workflow action: {action_type}")

        maybe_outcome = step_function(self, state, step_query, options)
        outcome = await maybe_outcome if isawaitable(maybe_outcome) else maybe_outcome
        if action_type == WorkflowActionType.PLAN_HOST_ACTIONS:
            for action in state.task.host_actions:
                if action.job_id is None:
                    action.job_id = job.job_id
        if tuple(outcome.artifacts) != spec.writes:
            raise RuntimeError(
                f"{action_type} wrote {tuple(outcome.artifacts)}, expected {spec.writes}."
            )
        self.artifacts.record_step_outcome(state, job, outcome, spec.output)
        job.metadata["artifacts_read"] = [artifact.value for artifact in spec.reads]
        job.metadata["artifacts_written"] = [artifact.value for artifact in spec.writes]


WorkflowStepFunction = Callable[
    [WorkflowStepExecutor, WorkflowState, RetrievalQuery, JsonObject],
    StepOutcome | Awaitable[StepOutcome],
]
