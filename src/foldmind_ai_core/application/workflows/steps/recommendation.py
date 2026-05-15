from __future__ import annotations

from typing import TYPE_CHECKING

from foldmind_ai_core.application.workflows.state.execution import (
    StepOutcome,
    WorkflowArtifactName,
)
from foldmind_ai_core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.application.workflows.steps.options import document_from_task
from foldmind_ai_core.application.workflows.steps.retrieval import (
    document_retrieval_or_search,
    folder_retrieval_or_search,
    retrieved_document_from_result,
)
from foldmind_ai_core.domain.generation.results import (
    DocumentRecommendation,
    DocumentRecommendationResult,
    FolderRecommendation,
    FolderRecommendationResult,
    RelatedRecommendationItem,
    RelatedRecommendationResult,
)
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.shared.types import Metadata

if TYPE_CHECKING:
    from foldmind_ai_core.application.workflows.steps.executor import WorkflowStepExecutor


def recommend_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    result = document_recommendations(ctx, state, query)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.DOCUMENT_RECOMMENDATION: result,
        },
        output=result,
    )


def recommend_folder(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    source = document_from_task(state, query, options)
    result = ctx.recommend_folder.execute(source)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.FOLDER_RECOMMENDATION: result,
        },
        output=result,
    )


def recommend_related(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    result = related_recommendations(ctx, state, query)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.RELATED_RECOMMENDATION: result,
        },
        output=result,
    )


def document_recommendations(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
) -> DocumentRecommendationResult:
    recommendations: list[DocumentRecommendation] = []
    for result in document_retrieval_or_search(ctx, state, query):
        recommendations.append(
            DocumentRecommendation(
                document=retrieved_document_from_result(result),
                reason="Document chunk is relevant to the request.",
                score=result.score,
                evidence=[result],
            )
        )
    return DocumentRecommendationResult(
        primary=recommendations[0] if recommendations else None,
        alternatives=recommendations[1:],
    )


def folder_recommendation_from_retrieval(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
) -> FolderRecommendationResult | None:
    existing = ctx.artifacts.folder_recommendation(state)
    if existing is not None:
        return existing

    recommendations: list[FolderRecommendation] = []
    for result in folder_retrieval_or_search(ctx, state, query, {}):
        recommendations.append(
            FolderRecommendation(
                folder_id=result.folder.folder_id,
                reason=result.reason or "Folder is relevant to the request.",
                score=result.score,
            )
        )
    if not recommendations:
        return None
    return FolderRecommendationResult(
        primary=recommendations[0],
        alternatives=recommendations[1:],
    )


def related_recommendations(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
) -> RelatedRecommendationResult:
    document_result = ctx.artifacts.document_recommendation(state)
    if document_result is None:
        document_result = document_recommendations(ctx, state, query)
    folder_result = folder_recommendation_from_retrieval(ctx, state, query)

    items: list[RelatedRecommendationItem] = []
    if document_result.primary is not None:
        items.append(RelatedRecommendationItem(target=document_result.primary))
    for document_recommendation in document_result.alternatives:
        items.append(RelatedRecommendationItem(target=document_recommendation))
    if folder_result is not None:
        items.append(RelatedRecommendationItem(target=folder_result.primary))
        for folder_recommendation in folder_result.alternatives:
            items.append(RelatedRecommendationItem(target=folder_recommendation))
    return RelatedRecommendationResult(items=items)
