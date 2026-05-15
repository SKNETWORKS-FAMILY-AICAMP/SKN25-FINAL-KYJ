from __future__ import annotations

from foldmind_ai_core.application.agents.answer_generator_agent import AnswerGeneratorAgent
from foldmind_ai_core.application.agents.draft_generator_agent import DraftGeneratorAgent
from foldmind_ai_core.application.agents.ideas_explorer_agent import IdeasExplorerAgent
from foldmind_ai_core.application.agents.planning_agent import PlanningAgent
from foldmind_ai_core.application.agents.summarizer_agent import SummarizerAgent
from foldmind_ai_core.application.ports.outbound.llm import LLM
from foldmind_ai_core.application.ports.outbound.prompt_repository import PromptRepositoryPort
from foldmind_ai_core.application.services.use_case_contracts import (
    DocumentFinder,
    FolderFinder,
    FolderRecommender,
)
from foldmind_ai_core.application.workflows.artifacts.store import WorkflowArtifactStore
from foldmind_ai_core.application.workflows.engine import WorkflowEngine
from foldmind_ai_core.application.workflows.host_actions.builder import HostActionBuilder
from foldmind_ai_core.application.workflows.host_actions.result_handler import (
    HostActionResultHandler,
)
from foldmind_ai_core.application.workflows.plan_compiler import WorkflowPlanCompiler
from foldmind_ai_core.application.workflows.steps.executor import WorkflowStepExecutor


def _build_workflow_engine(
    *,
    llm: LLM,
    prompt_repository: PromptRepositoryPort,
    find_documents: DocumentFinder,
    find_folders: FolderFinder,
    recommend_folder: FolderRecommender,
    answer_generator: AnswerGeneratorAgent,
) -> WorkflowEngine:
    host_action_results = HostActionResultHandler()
    artifacts = WorkflowArtifactStore()
    summarizer = SummarizerAgent(llm=llm, prompt_repository=prompt_repository)
    return WorkflowEngine(
        planning_agent=PlanningAgent(llm=llm, prompt_repository=prompt_repository),
        plan_compiler=WorkflowPlanCompiler(),
        step_executor=WorkflowStepExecutor(
            find_documents=find_documents,
            find_folders=find_folders,
            recommend_folder=recommend_folder,
            answer_generator=answer_generator,
            summarizer=summarizer,
            draft_generator=DraftGeneratorAgent(
                llm=llm,
                prompt_repository=prompt_repository,
            ),
            ideas_explorer=IdeasExplorerAgent(
                llm=llm,
                prompt_repository=prompt_repository,
            ),
            host_action_builder=HostActionBuilder(),
            artifacts=artifacts,
            host_action_results=host_action_results,
        ),
        host_action_results=host_action_results,
    )
