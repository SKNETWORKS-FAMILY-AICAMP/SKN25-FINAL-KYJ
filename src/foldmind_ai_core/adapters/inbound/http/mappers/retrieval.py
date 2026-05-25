from __future__ import annotations

from foldmind_ai_core.adapters.inbound.http.dtos.retrieval import RetrievalResultDTO
from foldmind_ai_core.adapters.inbound.http.mappers.transport_values import (
    transport_value,
)
from foldmind_ai_core.core.application.models.retrieval import RetrievalResult


def retrieval_result_dto_from_result(
    result: RetrievalResult,
) -> RetrievalResultDTO:
    chunk = result.chunk
    return RetrievalResultDTO(
        tenant=chunk.tenant,
        document_type=chunk.document_type,
        document_id=chunk.document_id,
        source_version=chunk.source_version,
        created_at=chunk.created_at,
        updated_at=chunk.updated_at,
        chunk_id=chunk.chunk_id,
        chunk_index=chunk.chunk_index,
        text=chunk.text,
        score=result.score,
        start_offset=chunk.start_offset,
        end_offset=chunk.end_offset,
        metadata=transport_value(chunk.metadata),
    )
