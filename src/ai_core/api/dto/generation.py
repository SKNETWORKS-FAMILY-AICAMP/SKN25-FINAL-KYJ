from __future__ import annotations

from pydantic import Field

from ai_core.api.dto.base import APIBaseDTO
from ai_core.api.dto.retrieval import RetrievalResultDTO
from ai_core.application.models.results import (
    AssistantClarification,
    DraftResult,
    GeneratedTextResult,
)


class AssistantClarificationDTO(APIBaseDTO):
    question: str
    reason: str

    @classmethod
    def from_model(cls, clarification: AssistantClarification) -> AssistantClarificationDTO:
        return cls(question=clarification.question, reason=clarification.reason)


class GeneratedTextResponse(APIBaseDTO):
    text: str
    citations: list[RetrievalResultDTO] = Field(default_factory=list)

    @classmethod
    def from_model(cls, result: GeneratedTextResult) -> GeneratedTextResponse:
        return cls(
            text=result.text,
            citations=[RetrievalResultDTO.from_model(citation) for citation in result.citations],
        )


class DraftResultDTO(APIBaseDTO):
    draft: str
    citations: list[RetrievalResultDTO] = Field(default_factory=list)

    @classmethod
    def from_model(cls, result: DraftResult) -> DraftResultDTO:
        return cls(
            draft=result.draft,
            citations=[RetrievalResultDTO.from_model(citation) for citation in result.citations],
        )
