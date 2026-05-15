from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from foldmind_ai_core.application.agents.answer_generator_agent import AnswerGeneratorAgent
from foldmind_ai_core.application.agents.draft_generator_agent import DraftGeneratorAgent
from foldmind_ai_core.application.agents.ideas_explorer_agent import IdeasExplorerAgent
from foldmind_ai_core.application.agents.summarizer_agent import SummarizerAgent
from foldmind_ai_core.application.services.use_case_contracts import (
    DocumentFinder,
    FolderFinder,
    FolderRecommender,
)
from foldmind_ai_core.application.workflows.artifacts.store import WorkflowArtifactStore
from foldmind_ai_core.application.workflows.host_actions.builder import HostActionBuilder
from foldmind_ai_core.application.workflows.host_actions.result_handler import (
    HostActionResultHandler,
)
from foldmind_ai_core.application.workflows.state.execution import (
    StepOutcome,
    WorkflowStepExecution,
)
from foldmind_ai_core.application.workflows.state.plan import WorkflowActionType
from foldmind_ai_core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.application.workflows.steps.generation import (
    answer_question,
    explore_ideas,
    generate_draft,
    summarize_documents,
    synthesize_report,
)
from foldmind_ai_core.application.workflows.steps.host_action import plan_host_actions
from foldmind_ai_core.application.workflows.steps.recommendation import (
    recommend_documents,
    recommend_folder,
    recommend_related,
)
from foldmind_ai_core.application.workflows.steps.retrieval import (
    analyze_documents,
    classify_documents,
    find_documents,
    find_folders,
    find_related,
)
from foldmind_ai_core.application.workflows.steps.specs import STEP_SPECS
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.shared.types import Metadata


@dataclass(slots=True)
class WorkflowStepExecutor:
    find_documents: DocumentFinder
    find_folders: FolderFinder
    recommend_folder: FolderRecommender
    answer_generator: AnswerGeneratorAgent
    summarizer: SummarizerAgent
    draft_generator: DraftGeneratorAgent
    ideas_explorer: IdeasExplorerAgent
    host_action_builder: HostActionBuilder
    artifacts: WorkflowArtifactStore
    host_action_results: HostActionResultHandler
    _handlers: dict[WorkflowActionType, StepHandler] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._handlers = {
            WorkflowActionType.FIND_DOCUMENTS: find_documents,
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
        }

    def execute(
        self,
        state: WorkflowState,
        action_type: WorkflowActionType,
        step_query: AIQuery,
        options: Metadata,
        execution: WorkflowStepExecution,
    ) -> None:
        spec = STEP_SPECS.get(action_type)
        handler = self._handlers.get(action_type)
        if spec is None or handler is None:
            raise NotImplementedError(f"Unsupported workflow action: {action_type}")

        outcome = handler(self, state, step_query, options)
        if tuple(outcome.artifacts) != spec.writes:
            raise RuntimeError(
                f"{action_type} wrote {tuple(outcome.artifacts)}, "
                f"expected {spec.writes}."
            )
        self.artifacts.record_step_outcome(state, outcome, spec.output)
        execution.artifacts_read = spec.reads
        execution.artifacts_written = spec.writes


StepHandler = Callable[
    [WorkflowStepExecutor, WorkflowState, AIQuery, Metadata],
    StepOutcome,
]
