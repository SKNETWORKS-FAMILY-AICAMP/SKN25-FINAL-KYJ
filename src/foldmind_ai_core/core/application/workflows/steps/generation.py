from __future__ import annotations

from typing import TYPE_CHECKING

from foldmind_ai_core.core.application.workflows.state.execution import (
    StepOutcome,
    WorkflowArtifactName,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.workflows.option_values import (
    instruction_option,
    normalized_string_value,
)
from foldmind_ai_core.core.application.services.prompts import (
    PROMPT_ANSWER_GENERATION,
    PROMPT_DRAFT_GENERATION,
    PROMPT_IDEAS_EXPLORATION,
    PROMPT_SUMMARIZATION,
)
from foldmind_ai_core.core.domain.models.generation.results import (
    AssistantClarification,
    DraftResult,
    GeneratedTextResult,
)
from foldmind_ai_core.core.application.queries.retrieval import RetrievalQuery
from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult
from foldmind_ai_core.shared.types import JsonObject

if TYPE_CHECKING:
    from foldmind_ai_core.core.application.workflows.steps.executor import WorkflowStepExecutor


def request_clarification(
    _ctx: WorkflowStepExecutor,
    _state: WorkflowState,
    _query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    result = AssistantClarification(
        question=normalized_string_value(
            options.get("question"),
            name="question",
            default="어떤 문서 또는 폴더를 말하는지 알려주세요.",
        ),
        reason=normalized_string_value(
            options.get("reason"),
            name="reason",
            default="요청을 처리하려면 대상 문서나 폴더가 필요합니다.",
        ),
    )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.CLARIFICATION: result,
        },
        output=result,
    )


def synthesize_report(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    _query: RetrievalQuery,
    _options: JsonObject,
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
    _query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    result = ctx.context_generator.generate(
        prompt_name=PROMPT_ANSWER_GENERATION,
        instruction=instruction_option(options),
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
    _query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    result = ctx.context_generator.generate(
        prompt_name=PROMPT_SUMMARIZATION,
        instruction=instruction_option(options),
        citations=ctx.artifacts.document_retrieval(state),
    )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.SUMMARY: result,
        },
        output=result,
    )


def generate_draft(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    _query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    generated = ctx.context_generator.generate(
        prompt_name=PROMPT_DRAFT_GENERATION,
        instruction=instruction_option(options),
        citations=ctx.artifacts.document_retrieval(state),
    )
    result = DraftResult(draft=generated.text, citations=generated.citations)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.DRAFT: result,
        },
        output=result,
    )


def explore_ideas(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    _query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    result = ctx.context_generator.generate(
        prompt_name=PROMPT_IDEAS_EXPLORATION,
        instruction=instruction_option(options),
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
    citations: list[RetrievalResult] = []
    for summary in summaries:
        citations.extend(summary.citations)

    return GeneratedTextResult(
        text="\n\n".join(summary.text for summary in summaries),
        citations=citations,
    )
