from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from foldmind_ai_core.core.application.factories.retrieval_results import (
    folder_search_results_to_domain,
    signal_search_results_to_domain,
)
from foldmind_ai_core.core.application.queries.retrieval import (
    FolderSearchQuery,
    RetrievalQuery,
)
from foldmind_ai_core.core.application.services.prompts import PROMPT_SUMMARIZATION
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.domain.models.generation.results import (
    DocumentSearchItem,
    DocumentSearchResult,
    GeneratedTextResult,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.retrieval.results import (
    FolderRetrievalResult,
    RelatedRetrievalItem,
    RelatedRetrievalResult,
    RetrievalResult,
    RetrievedDocument,
    RetrievedSignal,
    RetrievedSignalEvidence,
    SignalRetrievalResult,
)
from foldmind_ai_core.shared.types import JsonObject

if TYPE_CHECKING:
    from foldmind_ai_core.core.application.workflows.steps.executor import WorkflowStepExecutor

SIGNAL_EVIDENCE_CHUNKING_VERSION = "signal-evidence-v1"
SIGNAL_EVIDENCE_EMBEDDING_MODEL = "not-embedded"
SIGNAL_EVIDENCE_EMBEDDING_VERSION = "not-embedded"
SIGNAL_EVIDENCE_INDEX_SCHEMA_VERSION = "signal-evidence-v1"


def document_summaries(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    *,
    instruction: str,
) -> list[GeneratedTextResult]:
    retrieval = ctx.artifacts.document_retrieval(state)
    summaries: list[GeneratedTextResult] = []
    for document in relevant_documents(ctx, state):
        document_results = [
            result
            for result in retrieval
            if result.chunk.tenant == document.tenant
            and result.chunk.document_id == document.document_id
        ]
        if not document_results:
            continue
        summaries.append(
            ctx.context_generator.generate(
                prompt_name=PROMPT_SUMMARIZATION,
                instruction=instruction,
                citations=document_results,
            )
        )
    return summaries


def document_search_result(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
) -> DocumentSearchResult:
    items_by_document: dict[tuple[str, str], DocumentSearchItem] = {}
    for result in document_retrieval_or_search(ctx, state, query):
        document = retrieved_document_from_result(result)
        key = (document.tenant, document.document_id)
        item = items_by_document.get(key)
        if item is None:
            items_by_document[key] = DocumentSearchItem(
                document=document,
                score=result.score,
                reason="Document matches the search request.",
                evidence=[result],
            )
            continue
        item.evidence.append(result)
        if result.score > item.score:
            item.score = result.score
            item.document = document

    items = list(items_by_document.values())
    items.sort(key=lambda item: item.score, reverse=True)
    return DocumentSearchResult(items=items)


def signal_search_result(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
) -> GeneratedTextResult:
    signals = signal_retrieval_or_search(ctx, state, query)
    if not signals:
        return GeneratedTextResult(text="관련 signal을 찾지 못했습니다.", citations=[])
    lines = [
        f"- [{result.signal.signal_type}] {result.signal.text}"
        for result in signals
    ]
    return GeneratedTextResult(
        text="\n".join(lines),
        citations=signal_evidence_or_expand(ctx, state, signals),
    )


def signal_synthesis_instruction(
    *,
    instruction: str,
    signals: list[SignalRetrievalResult],
) -> str:
    signal_lines = [
        f"- [{result.signal.signal_type}] {result.signal.text}"
        for result in signals
    ]
    return "\n".join(
        (
            instruction,
            "",
            "다음 knowledge signals를 중심으로 답변하되, 근거 citation에 없는 내용은 단정하지 않는다.",
            *signal_lines,
        )
    )


def signal_evidence_or_expand(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    signals: list[SignalRetrievalResult],
) -> list[RetrievalResult]:
    existing = ctx.artifacts.optional_signal_evidence(state)
    if existing is not None:
        return existing
    return signal_evidence_from_results(signals)


def signal_evidence_from_results(
    signals: list[SignalRetrievalResult],
) -> list[RetrievalResult]:
    results: list[RetrievalResult] = []
    seen: set[tuple[str, str]] = set()
    for result in signals:
        signal = result.signal
        if signal.evidence:
            for evidence in signal.evidence:
                key = (signal.signal_id, evidence.chunk_id)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    RetrievalResult(
                        chunk=signal_evidence_chunk(result, evidence),
                        score=result.score,
                    )
                )
            continue
        key = (signal.signal_id, signal.signal_id)
        if key in seen:
            continue
        seen.add(key)
        results.append(
            RetrievalResult(
                chunk=signal_text_chunk(result),
                score=result.score,
            )
        )
    return results


def merge_signal_results(
    *groups: list[SignalRetrievalResult],
) -> list[SignalRetrievalResult]:
    merged: dict[str, SignalRetrievalResult] = {}
    for group in groups:
        for result in group:
            existing = merged.get(result.signal.signal_id)
            if existing is None or result.score > existing.score:
                merged[result.signal.signal_id] = result
    return sorted(merged.values(), key=lambda result: result.score, reverse=True)


def on_demand_signals_from_documents(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
    *,
    signal_type: str,
    top_k: int,
) -> list[SignalRetrievalResult]:
    results: list[SignalRetrievalResult] = []
    for retrieval in document_retrieval_or_search(ctx, state, query)[:top_k]:
        chunk = retrieval.chunk
        signal_id = _on_demand_signal_id(
            tenant=chunk.tenant,
            signal_type=signal_type,
            query_text=query.text,
            chunk_id=chunk.chunk_id,
        )
        results.append(
            SignalRetrievalResult(
                signal=RetrievedSignal(
                    signal_id=signal_id,
                    tenant=chunk.tenant,
                    document_type=chunk.document_type,
                    signal_type=signal_type,
                    signal_key=signal_id.removeprefix("on-demand-signal-")[:16],
                    text=chunk.text,
                    document_id=chunk.document_id,
                    source_version=chunk.source_version,
                    evidence=(
                        RetrievedSignalEvidence(
                            chunk_id=chunk.chunk_id,
                            quote=chunk.text,
                            start_offset=chunk.start_offset,
                            end_offset=chunk.end_offset,
                            metadata=dict(chunk.metadata),
                        ),
                    ),
                    metadata={"source": "on_demand_document_retrieval"},
                ),
                score=retrieval.score,
            )
        )
    return results


def signal_evidence_chunk(
    result: SignalRetrievalResult,
    evidence: RetrievedSignalEvidence,
) -> DocumentChunk:
    signal = result.signal
    return _document_chunk_for_signal(
        signal=signal,
        chunk_id=evidence.chunk_id,
        text=evidence.quote,
        start_offset=evidence.start_offset if evidence.start_offset is not None else 0,
        end_offset=(
            evidence.end_offset if evidence.end_offset is not None else len(evidence.quote)
        ),
        metadata={
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type,
            **dict(evidence.metadata),
        },
    )


def signal_text_chunk(result: SignalRetrievalResult) -> DocumentChunk:
    signal = result.signal
    return _document_chunk_for_signal(
        signal=signal,
        chunk_id=signal.signal_id,
        text=signal.text,
        start_offset=0,
        end_offset=len(signal.text),
        metadata={
            "signal_id": signal.signal_id,
            "signal_type": signal.signal_type,
            "source": "signal_text",
        },
    )


def signal_retrieval_or_search(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
) -> list[SignalRetrievalResult]:
    existing = ctx.artifacts.signal_retrieval(state)
    if existing:
        return existing
    return signal_search_results_to_domain(ctx.find_signals.execute(query))


def document_retrieval_or_search(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
) -> list[RetrievalResult]:
    retrieval = ctx.artifacts.optional_document_retrieval(state)
    if retrieval is not None:
        return retrieval
    return list(ctx.find_documents.execute(query).results)


def folder_retrieval_or_search(
    ctx: WorkflowStepExecutor,
    state: WorkflowState,
    query: RetrievalQuery,
) -> list[FolderRetrievalResult]:
    existing = ctx.artifacts.folder_retrieval(state)
    if existing is not None:
        return existing
    return folder_search_results_to_domain(
        ctx.find_folders.execute(folder_search_query_from_retrieval_query(query))
    )


def folder_search_query_from_retrieval_query(query: RetrievalQuery) -> FolderSearchQuery:
    return FolderSearchQuery(
        tenant=query.request_context.tenant,
        text=query.text,
        scope=query.scope,
    )


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
    items = [RelatedRetrievalItem(target=document) for document in documents]
    items.extend(RelatedRetrievalItem(target=folder) for folder in folders)
    items.sort(key=lambda item: item.score, reverse=True)
    return RelatedRetrievalResult(items=items)


def retrieved_documents_from_results(results: list[RetrievalResult]) -> list[RetrievedDocument]:
    documents: list[RetrievedDocument] = []
    seen: set[str] = set()
    for result in results:
        key = result.chunk.document_id
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
        created_at=result.chunk.created_at,
        updated_at=result.chunk.updated_at,
        snippet=result.chunk.text[:240],
        metadata=dict(result.chunk.metadata),
    )


def _on_demand_signal_id(
    *,
    tenant: str,
    signal_type: str,
    query_text: str,
    chunk_id: str,
) -> str:
    digest = hashlib.sha256(
        "\x1f".join((tenant, signal_type, query_text, chunk_id)).encode("utf-8")
    ).hexdigest()
    return f"on-demand-signal-{digest}"


def _document_chunk_for_signal(
    *,
    signal: RetrievedSignal,
    chunk_id: str,
    text: str,
    start_offset: int,
    end_offset: int,
    metadata: JsonObject,
) -> DocumentChunk:
    return DocumentChunk(
        tenant=signal.tenant,
        document_type=signal.document_type,
        document_id=signal.document_id
        or signal.related_document_id
        or signal.folder_id
        or "",
        source_version=signal.source_version,
        document_index_input_digest="signal-evidence-index-input-v1",
        created_at="",
        updated_at="",
        chunk_id=chunk_id,
        chunk_index=0,
        chunking_version=SIGNAL_EVIDENCE_CHUNKING_VERSION,
        text=text,
        text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        start_offset=start_offset,
        end_offset=end_offset,
        embedding_model=SIGNAL_EVIDENCE_EMBEDDING_MODEL,
        embedding_version=SIGNAL_EVIDENCE_EMBEDDING_VERSION,
        index_schema_version=SIGNAL_EVIDENCE_INDEX_SCHEMA_VERSION,
        metadata=metadata,
    )
