from __future__ import annotations

from typing import TYPE_CHECKING

from foldmind_ai_core.core.application.prompts import PROMPT_SUMMARIZATION
from foldmind_ai_core.core.application.models.retrieval import RetrievalQuery
from foldmind_ai_core.core.application.workflows.option_values import (
    bool_option,
    instruction_option,
    optional_text_option,
    positive_int_option,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    StepOutcome,
    WorkflowArtifactName,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.application.workflows.steps.retrieval_artifacts import (
    candidate_documents,
    document_retrieval_or_search,
    document_search_result,
    document_summaries,
    folder_retrieval_or_search,
    folder_search_query_from_retrieval_query,
    merge_signal_results,
    on_demand_signals_from_documents,
    related_retrieval,
    retrieved_documents_from_results,
    signal_evidence_from_results,
    signal_evidence_or_expand,
    signal_retrieval_or_search,
    signal_search_result,
    signal_synthesis_instruction,
)
from foldmind_ai_core.core.application.models.generation import GeneratedTextResult
from foldmind_ai_core.shared.types import JsonObject

if TYPE_CHECKING:
    from foldmind_ai_core.core.application.workflows.steps.executor import WorkflowStepExecutor


async def find_documents(
    ctx: WorkflowStepExecutor,
    _state: WorkflowState,
    query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    result = await ctx.document_search.search(
        query,
        require_comprehensive_search=bool_option(options, "require_comprehensive_search"),
    )
    results = list(result)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.DOCUMENT_RETRIEVAL: results,
            WorkflowArtifactName.CANDIDATE_DOCUMENTS: retrieved_documents_from_results(results),
        }
    )


async def find_folders(
    ctx: WorkflowStepExecutor,
    _state: WorkflowState,
    query: RetrievalQuery,
    _options: JsonObject,
) -> StepOutcome:
    folders = list(
        await ctx.folder_search.search(folder_search_query_from_retrieval_query(query))
    )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.FOLDER_RETRIEVAL: folders,
        }
    )


async def find_signals(
    ctx: WorkflowStepExecutor,
    _state: WorkflowState,
    query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    signals = list(
        await ctx.signal_search.search(
            query,
            signal_type=optional_text_option(options, "signal_type"),
            top_k=positive_int_option(options, "top_k", default=20),
        )
    )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.SIGNAL_RETRIEVAL: signals,
        }
    )


async def present_signals(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
    _options: JsonObject,
) -> StepOutcome:
    result = await signal_search_result(ctx, state, query)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.SIGNAL_SEARCH_RESULT: result,
        },
        output=result,
    )


async def expand_signal_evidence(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
    _options: JsonObject,
) -> StepOutcome:
    signals = await signal_retrieval_or_search(ctx, state, query)
    evidence = signal_evidence_from_results(signals)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.SIGNAL_EVIDENCE: evidence,
        }
    )


async def find_related(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
    _options: JsonObject,
) -> StepOutcome:
    documents = await document_retrieval_or_search(ctx, state, query)
    folders = await folder_retrieval_or_search(ctx, state, query)
    result = related_retrieval(documents, folders)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.RELATED_RETRIEVAL: result,
        }
    )


async def present_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
    _options: JsonObject,
) -> StepOutcome:
    result = await document_search_result(ctx, state, query)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.DOCUMENT_SEARCH_RESULT: result,
        },
        output=result,
    )


async def synthesize_signals(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    signals = await signal_retrieval_or_search(ctx, state, query)
    if not signals:
        result = GeneratedTextResult(text="관련 signal을 찾지 못했습니다.", citations=[])
    else:
        evidence = signal_evidence_or_expand(ctx, state, signals)
        result = await ctx.context_generator.generate(
            prompt_name=PROMPT_SUMMARIZATION,
            instruction=signal_synthesis_instruction(
                instruction=instruction_option(options),
                signals=signals,
            ),
            citations=evidence,
        )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.SUMMARY: result,
        },
        output=result,
    )


async def extract_on_demand_signals(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    existing = ctx.artifacts.signal_retrieval(state)
    min_signal_count = positive_int_option(options, "min_signal_count", default=1)
    signal_type = optional_text_option(options, "signal_type")
    top_k = positive_int_option(options, "top_k", default=20)
    if len(existing) >= min_signal_count:
        signals = existing
    else:
        indexed_signals = list(
            await ctx.signal_search.search(
                query,
                signal_type=signal_type,
                top_k=top_k,
            )
        )
        signals = merge_signal_results(
            existing,
            indexed_signals,
            await on_demand_signals_from_documents(
                ctx,
                state,
                query,
                signal_type=signal_type or "claim",
                top_k=top_k,
            ),
        )
    evidence = signal_evidence_from_results(signals)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.SIGNAL_RETRIEVAL: signals,
            WorkflowArtifactName.SIGNAL_EVIDENCE: evidence,
        }
    )


def classify_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    _query: RetrievalQuery,
    _options: JsonObject,
) -> StepOutcome:
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.RELEVANT_DOCUMENTS: candidate_documents(ctx, state),
        }
    )


async def analyze_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    _query: RetrievalQuery,
    options: JsonObject,
) -> StepOutcome:
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.DOCUMENT_SUMMARIES: await document_summaries(
                ctx,
                state,
                instruction=instruction_option(options),
            ),
        }
    )
