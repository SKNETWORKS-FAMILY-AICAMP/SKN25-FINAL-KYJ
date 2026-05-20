from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.dtos.retrieval import RetrievalResultDTO
from foldmind_ai_core.adapters.inbound.http.mappers.transport_values import (
    transport_value,
)
from foldmind_ai_core.core.application.results.retrieval import RetrievedChunkResult


def retrieval_result_dto_from_result(
    result: RetrievedChunkResult,
) -> RetrievalResultDTO:
    return RetrievalResultDTO(
        tenant=result.tenant,
        document_type=result.document_type,
        document_id=result.document_id,
        source_version=result.source_version,
        created_at=result.created_at,
        updated_at=result.updated_at,
        chunk_id=result.chunk_id,
        chunk_index=result.chunk_index,
        text=result.text,
        score=result.score,
        start_offset=result.start_offset,
        end_offset=result.end_offset,
        metadata=transport_value(result.metadata),
    )

