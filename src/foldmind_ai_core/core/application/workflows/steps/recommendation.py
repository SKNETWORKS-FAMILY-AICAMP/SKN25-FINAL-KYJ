from __future__ import annotations

from typing import TYPE_CHECKING

from foldmind_ai_core.core.application.commands.recommendation import RecommendFolderCommand
from foldmind_ai_core.core.application.factories.retrieval_results import (
    folder_recommendation_result_to_domain,
)
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.services.folder_recommendation_source_resolver import (
    FolderRecommendationSourceRequest,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    StepOutcome,
    WorkflowArtifactName,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.workflows.steps.retrieval_artifacts import (
    document_retrieval_or_search,
    folder_retrieval_or_search,
    retrieved_document_from_result,
)
from foldmind_ai_core.core.domain.models.generation.results import (
    DocumentRecommendation,
    DocumentRecommendationResult,
    FolderRecommendation,
    FolderRecommendationResult,
    RelatedRecommendationItem,
    RelatedRecommendationResult,
)
from foldmind_ai_core.shared.types import JsonObject

if TYPE_CHECKING:
    from foldmind_ai_core.core.application.workflows.steps.executor import WorkflowStepExecutor


def recommend_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
    _options: JsonObject,
) -> StepOutcome:
    result = _document_recommendations(ctx, state, query)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.DOCUMENT_RECOMMENDATION: result,
        },
        output=result,
    )


def recommend_folder(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    source = ctx.folder_recommendation_sources.resolve(
        FolderRecommendationSourceRequest(
            tenant=state.task.tenant,
            request_text=query.text,
            requested_at=query.request_context.requested_at,
            context_document_id=query.request_context.document_id,
            context_folder_id=query.request_context.folder_id,
            task_document=state.task.metadata.get("document"),
            options=options,
        )
    )
    document = source.document
    result = folder_recommendation_result_to_domain(
        ctx.recommend_folder.execute(
            RecommendFolderCommand(
                tenant=document.tenant,
                document_type=document.document_type,
                document_id=document.document_id,
                source_version=document.source_version,
                title=document.title,
                body=document.body,
                created_at=document.created_at,
                updated_at=document.updated_at,
                folder_ids=source.folder_ids,
                metadata=dict(document.metadata),
            )
        )
    )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.FOLDER_RECOMMENDATION: result,
        },
        output=result,
    )


def recommend_related(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
    _options: JsonObject,
) -> StepOutcome:
    document_result = ctx.artifacts.document_recommendation(state)
    if document_result is None:
        document_result = _document_recommendations(ctx, state, query)
    folder_result = ctx.artifacts.folder_recommendation(state)
    if folder_result is None:
        folder_recommendations = [
            FolderRecommendation(
                folder_id=folder_retrieval.folder.folder_id,
                reason=folder_retrieval.reason or "Folder is relevant to the request.",
                score=folder_retrieval.score,
            )
            for folder_retrieval in folder_retrieval_or_search(ctx, state, query)
        ]
        if folder_recommendations:
            folder_result = FolderRecommendationResult(
                primary=folder_recommendations[0],
                alternatives=folder_recommendations[1:],
            )

    items: list[RelatedRecommendationItem] = []
    if document_result.primary is not None:
        items.append(RelatedRecommendationItem(target=document_result.primary))
    items.extend(
        RelatedRecommendationItem(target=document_recommendation)
        for document_recommendation in document_result.alternatives
    )
    if folder_result is not None:
        items.append(RelatedRecommendationItem(target=folder_result.primary))
        items.extend(
            RelatedRecommendationItem(target=folder_recommendation)
            for folder_recommendation in folder_result.alternatives
        )
    items.sort(key=lambda item: item.score, reverse=True)
    related_recommendations = RelatedRecommendationResult(items=items)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.RELATED_RECOMMENDATION: related_recommendations,
        },
        output=related_recommendations,
    )


def _document_recommendations(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
) -> DocumentRecommendationResult:
    recommendations = [
        DocumentRecommendation(
            document=retrieved_document_from_result(result),
            reason="Document chunk is relevant to the request.",
            score=result.score,
            evidence=[result],
        )
        for result in document_retrieval_or_search(ctx, state, query)
    ]
    return DocumentRecommendationResult(
        primary=recommendations[0] if recommendations else None,
        alternatives=recommendations[1:],
    )
