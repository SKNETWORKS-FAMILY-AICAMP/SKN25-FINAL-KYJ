from __future__ import annotations

from typing import Any

from foldmind_ai_core.adapters.outbound.workflow_runtime.graph import LangGraphWorkflowGraph
from foldmind_ai_core.bootstrap.container.checkpointing import _build_workflow_checkpointer
from foldmind_ai_core.bootstrap.settings import APISettings
from foldmind_ai_core.core.application.agents.planning_agent import PlanningAgent
from foldmind_ai_core.core.application.ports.outbound.provider.llm import LLMProvider
from foldmind_ai_core.core.application.ports.outbound.provider.prompt_store import PromptStore
from foldmind_ai_core.core.application.ports.outbound.runtime.workflow_runtime import (
    WorkflowRuntime,
)
from foldmind_ai_core.core.application.services.recommendation.folder_recommendation_service import (  # noqa: E501
    FolderRecommendationService,
)
from foldmind_ai_core.core.application.services.recommendation.folder_recommendation_source_resolver import (  # noqa: E501
    FolderRecommendationSourceResolver,
)
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
from foldmind_ai_core.core.application.workflows.engine import WorkflowEngine
from foldmind_ai_core.core.application.workflows.host_actions.builder import HostActionBuilder
from foldmind_ai_core.core.application.workflows.host_actions.result_service import (
    HostActionResultService,
)
from foldmind_ai_core.core.application.workflows.plan_compiler import WorkflowPlanCompiler
from foldmind_ai_core.core.application.workflows.steps.executor import (
    ContextGenerator,
    WorkflowStepExecutor,
)


def _build_workflow_engine(
    *,
    llm: LLMProvider,
    prompt_store: PromptStore,
    document_search: DocumentSearchService,
    signal_search: SignalSearchService,
    folder_search: FolderSearchService,
    folder_recommendation: FolderRecommendationService,
    folder_recommendation_sources: FolderRecommendationSourceResolver,
    context_generator: ContextGenerator,
) -> WorkflowEngine:
    host_action_results = HostActionResultService()
    artifacts = WorkflowArtifactRegistry()
    return WorkflowEngine(
        planning=PlanningAgent(llm=llm, prompt_store=prompt_store),
        plan_compiler=WorkflowPlanCompiler(),
        step_executor=WorkflowStepExecutor(
            document_search=document_search,
            signal_search=signal_search,
            folder_search=folder_search,
            folder_recommendation=folder_recommendation,
            folder_recommendation_sources=folder_recommendation_sources,
            context_generator=context_generator,
            host_action_builder=HostActionBuilder(),
            artifacts=artifacts,
            host_action_results=host_action_results,
        ),
        host_action_results=host_action_results,
    )


def _build_workflow_runtime(
    *,
    settings: APISettings,
    llm: LLMProvider,
    prompt_store: PromptStore,
    document_search: DocumentSearchService,
    signal_search: SignalSearchService,
    folder_search: FolderSearchService,
    folder_recommendation: FolderRecommendationService,
    folder_recommendation_sources: FolderRecommendationSourceResolver,
    context_generator: ContextGenerator,
    checkpointer: Any | None = None,
) -> WorkflowRuntime:
    if checkpointer is None:
        checkpointer = _build_workflow_checkpointer(settings)
    return LangGraphWorkflowGraph(
        engine=_build_workflow_engine(
            llm=llm,
            prompt_store=prompt_store,
            document_search=document_search,
            signal_search=signal_search,
            folder_search=folder_search,
            folder_recommendation=folder_recommendation,
            folder_recommendation_sources=folder_recommendation_sources,
            context_generator=context_generator,
        ),
        checkpointer=checkpointer,
    )
