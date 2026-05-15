from __future__ import annotations

from typing import TYPE_CHECKING

from foldmind_ai_core.application.workflows.state.execution import (
    StepOutcome,
    WorkflowArtifactName,
)
from foldmind_ai_core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.domain.generation.results import GeneratedTextResult
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.retrieval.results import RetrievalResult
from foldmind_ai_core.shared.types import Metadata

if TYPE_CHECKING:
    from foldmind_ai_core.application.workflows.steps.executor import WorkflowStepExecutor


def synthesize_report(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    report = synthesized_report(ctx, state)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.SYNTHESIZED_REPORT: report,
        },
        output=report,
    )


def answer_question(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    result = ctx.answer_generator.answer(
        query=query,
        citations=ctx.artifacts.document_retrieval(state),
    )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.ANSWER: result,
        },
        output=result,
    )


def summarize_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    result = ctx.summarizer.summarize(ctx.artifacts.document_retrieval(state))
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.SUMMARY: result,
        },
        output=result,
    )


def generate_draft(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    result = ctx.draft_generator.generate(
        instruction=query.text,
        citations=ctx.artifacts.document_retrieval(state),
    )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.DRAFT: result,
        },
        output=result,
    )


def explore_ideas(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    result = ctx.ideas_explorer.explore(
        prompt=query.text,
        citations=ctx.artifacts.document_retrieval(state),
    )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.IDEAS: result,
        },
        output=result,
    )


def synthesized_report(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
) -> GeneratedTextResult:
    summaries = ctx.artifacts.document_summaries(state)
    if not summaries:
        return ctx.summarizer.summarize(ctx.artifacts.document_retrieval(state))

    citations: list[RetrievalResult] = []
    for summary in summaries:
        citations.extend(summary.citations)

    return GeneratedTextResult(
        text="\n\n".join(summary.text for summary in summaries),
        citations=citations,
    )
