from __future__ import annotations

from typing import Any

from foldmind_ai_core.adapters.outbound.workflow_runtime.graph import LangGraphWorkflowGraph
from foldmind_ai_core.bootstrap.container.checkpointing import build_workflow_checkpointer
from foldmind_ai_core.bootstrap.settings import APISettings
from foldmind_ai_core.core.application.agents.planning_agent import PlanningAgent
from foldmind_ai_core.core.application.capabilities.generation import (
    ContextGenerationCapability,
)
from foldmind_ai_core.core.application.capabilities.retrieval import (
    DocumentSearchCapability,
    FolderRecommendationCapability,
    FolderSearchCapability,
    SignalSearchCapability,
)
from foldmind_ai_core.core.application.ports.outbound.llm import LLMProvider
from foldmind_ai_core.core.application.ports.outbound.prompt_store import PromptStore
from foldmind_ai_core.core.application.ports.outbound.workflow_runtime import WorkflowRuntime
from foldmind_ai_core.core.application.services.folder_recommendation_source_resolver import (
    FolderRecommendationSourceResolver,
)
from foldmind_ai_core.core.application.workflows.artifacts.registry import (
    WorkflowArtifactRegistry,
)
from foldmind_ai_core.core.application.workflows.engine import WorkflowEngine
from foldmind_ai_core.core.application.workflows.host_actions.builder import HostActionBuilder
from foldmind_ai_core.core.application.workflows.host_actions.result_service import (
    HostActionResultService,
)
from foldmind_ai_core.core.application.workflows.plan_compiler import WorkflowPlanCompiler
from foldmind_ai_core.core.application.workflows.steps.executor import WorkflowStepExecutor


def build_workflow_engine(
    *,
    llm: LLMProvider,
    prompt_store: PromptStore,
    find_documents: DocumentSearchCapability,
    find_signals: SignalSearchCapability,
    find_folders: FolderSearchCapability,
    recommend_folder: FolderRecommendationCapability,
    folder_recommendation_sources: FolderRecommendationSourceResolver,
    context_generator: ContextGenerationCapability,
) -> WorkflowEngine:
    host_action_results = HostActionResultService()
    artifacts = WorkflowArtifactRegistry()
    return WorkflowEngine(
        planning=PlanningAgent(llm=llm, prompt_store=prompt_store),
        plan_compiler=WorkflowPlanCompiler(),
        step_executor=WorkflowStepExecutor(
            find_documents=find_documents,
            find_signals=find_signals,
            find_folders=find_folders,
            recommend_folder=recommend_folder,
            folder_recommendation_sources=folder_recommendation_sources,
            context_generator=context_generator,
            host_action_builder=HostActionBuilder(),
            artifacts=artifacts,
            host_action_results=host_action_results,
        ),
        host_action_results=host_action_results,
    )


def build_workflow_runtime(
    *,
    settings: APISettings,
    llm: LLMProvider,
    prompt_store: PromptStore,
    find_documents: DocumentSearchCapability,
    find_signals: SignalSearchCapability,
    find_folders: FolderSearchCapability,
    recommend_folder: FolderRecommendationCapability,
    folder_recommendation_sources: FolderRecommendationSourceResolver,
    context_generator: ContextGenerationCapability,
    checkpointer: Any | None = None,
) -> WorkflowRuntime:
    return LangGraphWorkflowGraph(
        engine=build_workflow_engine(
            llm=llm,
            prompt_store=prompt_store,
            find_documents=find_documents,
            find_signals=find_signals,
            find_folders=find_folders,
            recommend_folder=recommend_folder,
            folder_recommendation_sources=folder_recommendation_sources,
            context_generator=context_generator,
        ),
        checkpointer=checkpointer or build_workflow_checkpointer(settings),
    )
