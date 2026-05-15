from __future__ import annotations

from typing import TYPE_CHECKING

from foldmind_ai_core.application.workflows.state.execution import (
    StepOutcome,
    WorkflowArtifactName,
)
from foldmind_ai_core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.application.workflows.steps.options import (
    bool_option,
)
from foldmind_ai_core.domain.generation.results import GeneratedTextResult
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.retrieval.results import (
    FolderRetrievalResult,
    RelatedRetrievalItem,
    RelatedRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
)
from foldmind_ai_core.shared.types import Metadata

if TYPE_CHECKING:
    from foldmind_ai_core.application.workflows.steps.executor import WorkflowStepExecutor


def find_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    results = ctx.find_documents.execute(
        query,
        require_comprehensive_search=bool_option(options, "require_comprehensive_search"),
    )
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.DOCUMENT_RETRIEVAL: results,
            WorkflowArtifactName.CANDIDATE_DOCUMENTS: retrieved_documents_from_results(results),
        }
    )


def find_folders(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    folders = ctx.find_folders.execute(query)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.FOLDER_RETRIEVAL: folders,
        }
    )


def find_related(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    documents = document_retrieval_or_search(ctx, state, query)
    folders = folder_retrieval_or_search(ctx, state, query, options)
    result = related_retrieval(documents, folders)
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.RELATED_RETRIEVAL: result,
        }
    )


def classify_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.RELEVANT_DOCUMENTS: candidate_documents(ctx, state),
        }
    )


def analyze_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> StepOutcome:
    return StepOutcome(
        artifacts={
            WorkflowArtifactName.DOCUMENT_SUMMARIES: document_summaries(ctx, state),
        }
    )


def document_summaries(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
) -> list[GeneratedTextResult]:
    retrieval = ctx.artifacts.document_retrieval(state)
    summaries: list[GeneratedTextResult] = []
    for document in relevant_documents(ctx, state):
        document_results = [
            result
            for result in retrieval
            if result.chunk.tenant == document.tenant
            and result.chunk.document_type == document.document_type
            and result.chunk.document_id == document.document_id
        ]
        summaries.append(ctx.summarizer.summarize(document_results or retrieval))
    return summaries


def document_retrieval_or_search(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
) -> list[RetrievalResult]:
    retrieval = ctx.artifacts.document_retrieval(state)
    if retrieval:
        return retrieval
    return ctx.find_documents.execute(query)


def folder_retrieval_or_search(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: AIQuery,
    options: Metadata,
) -> list[FolderRetrievalResult]:
    existing = ctx.artifacts.folder_retrieval(state)
    if existing is None:
        return ctx.find_folders.execute(query)
    return existing


def candidate_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
) -> list[RetrievedDocument]:
    existing = ctx.artifacts.candidate_documents(state)
    if existing is None:
        return retrieved_documents_from_results(ctx.artifacts.document_retrieval(state))
    return existing


def relevant_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
) -> list[RetrievedDocument]:
    existing = ctx.artifacts.relevant_documents(state)
    if existing is None:
        return candidate_documents(ctx, state)
    return existing


def related_retrieval(
    documents: list[RetrievalResult],
    folders: list[FolderRetrievalResult],
) -> RelatedRetrievalResult:
    items: list[RelatedRetrievalItem] = []
    for document in documents:
        items.append(RelatedRetrievalItem(target=document))
    for folder in folders:
        items.append(RelatedRetrievalItem(target=folder))
    return RelatedRetrievalResult(items=items)


def retrieved_documents_from_results(results: list[RetrievalResult]) -> list[RetrievedDocument]:
    documents: list[RetrievedDocument] = []
    seen: set[tuple[str, str, str]] = set()
    for result in results:
        key = (result.chunk.tenant, result.chunk.document_type, result.chunk.document_id)
        if key in seen:
            continue
        seen.add(key)
        documents.append(retrieved_document_from_result(result))
    return documents


def retrieved_document_from_result(result: RetrievalResult) -> RetrievedDocument:
    return RetrievedDocument(
        tenant=result.chunk.tenant,
        document_type=result.chunk.document_type,
        document_id=result.chunk.document_id,
        source_version=result.chunk.source_version,
        snippet=result.chunk.text[:240],
        metadata=dict(result.chunk.metadata),
    )
