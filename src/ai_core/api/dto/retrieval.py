from __future__ import annotations

from typing import Any

from pydantic import Field

from ai_core.api.dto._plain import to_plain
from ai_core.api.dto.base import APIBaseDTO
from ai_core.api.dto.queries import AIQueryDTO
from ai_core.application.models.queries import AIQuery
from ai_core.application.models.retrieval import RetrievalResult


class SearchDocumentsRequest(APIBaseDTO):
    query: AIQueryDTO

    def to_model(self) -> AIQuery:
        return self.query.to_model()


class RetrievalResultDTO(APIBaseDTO):
    tenant: str
    entity_type: str
    entity_id: str
    version: str
    chunk_id: str
    chunk_index: int
    text: str
    score: float
    start_offset: int
    end_offset: int
    folder_ids: tuple[str, ...] = Field(default_factory=tuple)
    tags: tuple[str, ...] = Field(default_factory=tuple)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, result: RetrievalResult) -> RetrievalResultDTO:
        chunk = result.chunk
        return cls(
            tenant=chunk.tenant,
            entity_type=chunk.entity_type,
            entity_id=chunk.entity_id,
            version=chunk.version,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            score=result.score,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
            folder_ids=chunk.folder_ids,
            tags=chunk.tags,
            metadata=to_plain(chunk.metadata),
        )


class SearchDocumentsResponse(APIBaseDTO):
    results: list[RetrievalResultDTO] = Field(default_factory=list)

    @classmethod
    def from_model(cls, results: list[RetrievalResult]) -> SearchDocumentsResponse:
        return cls(results=[RetrievalResultDTO.from_model(result) for result in results])


class AnswerQuestionRequest(APIBaseDTO):
    query: AIQueryDTO

    def to_model(self) -> AIQuery:
        return self.query.to_model()
