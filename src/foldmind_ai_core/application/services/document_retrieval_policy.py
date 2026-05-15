from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from foldmind_ai_core.domain.retrieval.queries import SearchScope
from foldmind_ai_core.domain.retrieval.results import (
    DocumentRetrievalResult,
    RetrievalResult,
)


class SearchMode(StrEnum):
    DENSE = "dense"
    KEYWORD = "keyword"
    HYBRID = "hybrid"


@dataclass(slots=True)
class HybridSearchConfig:
    mode: SearchMode = SearchMode.HYBRID
    top_k: int = 5
    dense_top_k: int = 20
    document_top_k: int = 20
    graph_top_k: int = 20
    keyword_top_k: int = 20
    comprehensive_top_k: int = 100
    rrf_k: int = 60
    both_sources_bonus: float = 0.15


def reciprocal_rank_fusion(
    result_sets: list[list[RetrievalResult]],
    *,
    top_k: int,
    k: int,
) -> list[RetrievalResult]:
    scores: dict[tuple[str, str, str, str], float] = {}
    results_by_key: dict[tuple[str, str, str, str], RetrievalResult] = {}

    for results in result_sets:
        for rank, result in enumerate(results, start=1):
            key = chunk_result_key(result)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            results_by_key.setdefault(key, result)

    fused = [
        RetrievalResult(chunk=results_by_key[key].chunk, score=score)
        for key, score in scores.items()
    ]
    fused.sort(key=lambda result: result.score, reverse=True)
    return fused[:top_k]


def rank_document_candidates(
    *,
    document_results: list[DocumentRetrievalResult],
    graph_results: list[DocumentRetrievalResult],
    both_sources_bonus: float,
) -> list[DocumentRetrievalResult]:
    candidates: dict[tuple[str, str, str], DocumentRetrievalResult] = {}
    source_counts: dict[tuple[str, str, str], int] = {}

    for result in document_results:
        key = document_result_key(result)
        candidates[key] = result
        source_counts[key] = source_counts.get(key, 0) + 1

    for result in graph_results:
        key = document_result_key(result)
        existing = candidates.get(key)
        score = result.score
        if existing is not None:
            score = max(existing.score, result.score) + both_sources_bonus
            result = DocumentRetrievalResult(document=result.document, score=score)
        candidates[key] = result
        source_counts[key] = source_counts.get(key, 0) + 1

    ranked = list(candidates.values())
    ranked.sort(
        key=lambda result: (
            source_counts.get(document_result_key(result), 0),
            result.score,
        ),
        reverse=True,
    )
    return ranked


def candidate_scope(
    scope: SearchScope | None,
    candidates: list[DocumentRetrievalResult],
) -> SearchScope | None:
    if not candidates:
        return scope
    document_ids = tuple(
        dict.fromkeys(candidate.document.document_id for candidate in candidates)
    )
    document_type = candidates[0].document.document_type
    if scope is not None:
        return SearchScope(
            document_type=scope.document_type or document_type,
            document_id=scope.document_id,
            document_ids=scope.document_ids or document_ids,
            metadata_filter=dict(scope.metadata_filter),
        )
    return SearchScope(document_type=document_type, document_ids=document_ids)


def boost_chunk_results(
    results: list[RetrievalResult],
    candidates: list[DocumentRetrievalResult],
) -> list[RetrievalResult]:
    if not candidates:
        return results
    candidate_scores = {
        document_result_key(candidate): candidate.score for candidate in candidates
    }
    boosted = [
        RetrievalResult(
            chunk=result.chunk,
            score=result.score
            + 0.01
            * candidate_scores.get(
                (
                    result.chunk.tenant,
                    result.chunk.document_type,
                    result.chunk.document_id,
                ),
                0.0,
            ),
        )
        for result in results
    ]
    boosted.sort(key=lambda result: result.score, reverse=True)
    return boosted


def dedupe_results_by_document(results: list[RetrievalResult]) -> list[RetrievalResult]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[RetrievalResult] = []
    for result in results:
        key = (
            result.chunk.tenant,
            result.chunk.document_type,
            result.chunk.document_id,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def chunk_result_key(result: RetrievalResult) -> tuple[str, str, str, str]:
    return (
        result.chunk.tenant,
        result.chunk.document_type,
        result.chunk.document_id,
        result.chunk.chunk_id,
    )


def document_result_key(result: DocumentRetrievalResult) -> tuple[str, str, str]:
    return (
        result.document.tenant,
        result.document.document_type,
        result.document.document_id,
    )
