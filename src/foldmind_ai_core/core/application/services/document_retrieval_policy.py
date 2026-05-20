from __future__ import annotations

import math
from dataclasses import dataclass

from foldmind_ai_core.core.application.queries.retrieval import SearchScope
from foldmind_ai_core.core.domain.models.retrieval.results import (
    DocumentRetrievalResult,
    RetrievalResult,
)
from foldmind_ai_core.shared.validation import InvalidInputError


@dataclass(slots=True)
class DocumentRetrievalConfig:
    top_k: int = 5
    keyword_top_k: int = 20
    document_top_k: int = 20
    graph_top_k: int = 20
    comprehensive_top_k: int = 100
    both_sources_bonus: float = 0.15
    hybrid_rrf_k: int = 60

    def __post_init__(self) -> None:
        for field_name in (
            "top_k",
            "keyword_top_k",
            "document_top_k",
            "graph_top_k",
            "comprehensive_top_k",
            "hybrid_rrf_k",
        ):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise InvalidInputError(f"{field_name} must be a positive integer.")
        if (
            isinstance(self.both_sources_bonus, bool)
            or not isinstance(self.both_sources_bonus, int | float)
            or not math.isfinite(float(self.both_sources_bonus))
            or self.both_sources_bonus < 0.0
        ):
            raise InvalidInputError("both_sources_bonus must be a finite non-negative number.")


def rank_document_candidates(
    *,
    document_results: list[DocumentRetrievalResult],
    graph_results: list[DocumentRetrievalResult],
    both_sources_bonus: float,
) -> list[DocumentRetrievalResult]:
    document_candidates = _best_results_by_document(document_results)
    graph_candidates = _best_results_by_document(graph_results)
    candidate_keys = set(document_candidates) | set(graph_candidates)

    candidates: list[DocumentRetrievalResult] = []
    source_counts: dict[str, int] = {}
    for key in candidate_keys:
        document_candidate = document_candidates.get(key)
        graph_candidate = graph_candidates.get(key)
        if document_candidate is not None and graph_candidate is not None:
            score = max(document_candidate.score, graph_candidate.score) + both_sources_bonus
            candidates.append(
                DocumentRetrievalResult(
                    document=document_candidate.document,
                    score=score,
                )
            )
            source_counts[key] = 2
            continue
        candidate = document_candidate if document_candidate is not None else graph_candidates[key]
        candidates.append(candidate)
        source_counts[key] = 1

    candidates.sort(
        key=lambda result: (
            source_counts[result.document.document_id],
            result.score,
        ),
        reverse=True,
    )
    return candidates


def candidate_scope(
    scope: SearchScope | None,
    candidates: list[DocumentRetrievalResult],
) -> SearchScope | None:
    if not candidates:
        return scope
    document_ids = tuple(
        dict.fromkeys(candidate.document.document_id for candidate in candidates)
    )
    if scope is not None:
        has_explicit_document_scope = scope.document_id is not None or bool(
            scope.document_ids
        )
        scoped_document_ids = (
            scope.document_ids if has_explicit_document_scope else document_ids
        )
        return SearchScope(
            document_type=scope.document_type,
            document_id=scope.document_id,
            document_ids=scoped_document_ids,
            folder_ids=scope.folder_ids,
            created_at=scope.created_at,
            updated_at=scope.updated_at,
            sort=scope.sort,
            metadata_filter=dict(scope.metadata_filter),
        )
    return SearchScope(document_ids=document_ids)


def boost_chunk_results(
    results: list[RetrievalResult],
    candidates: list[DocumentRetrievalResult],
) -> list[RetrievalResult]:
    valid_results = [
        result
        for result in results
        if result.chunk.document_id.strip() and math.isfinite(result.score)
    ]
    if not candidates:
        return valid_results
    candidate_scores = {
        candidate.document.document_id: candidate.score for candidate in candidates
    }
    boosted = [
        RetrievalResult(
            chunk=result.chunk,
            score=result.score
            + 0.01
            * candidate_scores.get(result.chunk.document_id, 0.0),
        )
        for result in valid_results
    ]
    boosted.sort(key=lambda result: result.score, reverse=True)
    return boosted


def merge_hybrid_chunk_results(
    *,
    dense_results: list[RetrievalResult],
    keyword_results: list[RetrievalResult],
    rrf_k: int,
) -> list[RetrievalResult]:
    if not keyword_results:
        return dense_results
    if not dense_results:
        return keyword_results

    chunks_by_id: dict[str, RetrievalResult] = {}
    scores_by_id: dict[str, float] = {}
    for results in (dense_results, keyword_results):
        for rank, result in enumerate(results, start=1):
            chunk_id = result.chunk.chunk_id
            if not chunk_id.strip() or not math.isfinite(result.score):
                continue
            chunks_by_id.setdefault(chunk_id, result)
            scores_by_id[chunk_id] = scores_by_id.get(chunk_id, 0.0) + (
                1.0 / (rrf_k + rank)
            )

    merged = [
        RetrievalResult(chunk=chunks_by_id[chunk_id].chunk, score=score)
        for chunk_id, score in scores_by_id.items()
    ]
    merged.sort(key=lambda result: result.score, reverse=True)
    return merged


def dedupe_results_by_document(results: list[RetrievalResult]) -> list[RetrievalResult]:
    seen: set[str] = set()
    deduped: list[RetrievalResult] = []
    for result in results:
        key = result.chunk.document_id
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def _best_results_by_document(
    results: list[DocumentRetrievalResult],
) -> dict[str, DocumentRetrievalResult]:
    best_results: dict[str, DocumentRetrievalResult] = {}
    for result in results:
        if not result.document.document_id.strip() or not math.isfinite(result.score):
            continue
        key = result.document.document_id
        existing = best_results.get(key)
        if existing is None or result.score > existing.score:
            best_results[key] = result
    return best_results
