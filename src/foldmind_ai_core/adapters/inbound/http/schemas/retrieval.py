from __future__ import annotations

from typing import Any

from pydantic import Field

from foldmind_ai_core.adapters.inbound.http.schemas.base import APIBaseDTO, to_plain
from foldmind_ai_core.adapters.inbound.http.schemas.documents import (
    RetrievedDocumentDTO,
    SourceDocumentDTO,
)
from foldmind_ai_core.adapters.inbound.http.schemas.queries import AIQueryDTO
from foldmind_ai_core.domain.generation.results import (
    AssistantClarification,
    DocumentRecommendation,
    DocumentRecommendationResult,
    DraftResult,
    FolderRecommendation,
    FolderRecommendationResult,
    GeneratedTextResult,
    RelatedRecommendationItem,
    RelatedRecommendationResult,
)
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.retrieval.queries import AIQuery
from foldmind_ai_core.domain.retrieval.results import RetrievalResult


class SearchDocumentsRequest(APIBaseDTO):
    query: AIQueryDTO

    def to_model(self) -> AIQuery:
        return self.query.to_model()


class RetrievalResultDTO(APIBaseDTO):
    tenant: str
    document_type: str
    document_id: str
    source_version: str
    chunk_id: str
    chunk_index: int
    text: str
    score: float
    start_offset: int
    end_offset: int
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, result: RetrievalResult) -> RetrievalResultDTO:
        chunk = result.chunk
        return cls(
            tenant=chunk.tenant,
            document_type=chunk.document_type,
            document_id=chunk.document_id,
            source_version=chunk.source_version,
            chunk_id=chunk.chunk_id,
            chunk_index=chunk.chunk_index,
            text=chunk.text,
            score=result.score,
            start_offset=chunk.start_offset,
            end_offset=chunk.end_offset,
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


class RecommendFolderRequest(APIBaseDTO):
    document: SourceDocumentDTO

    def to_model(self) -> SourceDocument:
        return self.document.to_model()


class DocumentRecommendationDTO(APIBaseDTO):
    document: RetrievedDocumentDTO
    reason: str
    score: float
    evidence: list[RetrievalResultDTO] = Field(default_factory=list)

    @classmethod
    def from_model(cls, recommendation: DocumentRecommendation) -> DocumentRecommendationDTO:
        return cls(
            document=RetrievedDocumentDTO.from_model(recommendation.document),
            reason=recommendation.reason,
            score=recommendation.score,
            evidence=[
                RetrievalResultDTO.from_model(evidence) for evidence in recommendation.evidence
            ],
        )


class DocumentRecommendationResultDTO(APIBaseDTO):
    primary: DocumentRecommendationDTO | None = None
    alternatives: list[DocumentRecommendationDTO] = Field(default_factory=list)
    confidence: float

    @classmethod
    def from_model(
        cls,
        result: DocumentRecommendationResult,
    ) -> DocumentRecommendationResultDTO:
        return cls(
            primary=(
                DocumentRecommendationDTO.from_model(result.primary)
                if result.primary is not None
                else None
            ),
            alternatives=[
                DocumentRecommendationDTO.from_model(recommendation)
                for recommendation in result.alternatives
            ],
            confidence=result.confidence,
        )


class FolderRecommendationDTO(APIBaseDTO):
    folder_id: str
    reason: str
    score: float

    @classmethod
    def from_model(cls, recommendation: FolderRecommendation) -> FolderRecommendationDTO:
        return cls(
            folder_id=recommendation.folder_id,
            reason=recommendation.reason,
            score=recommendation.score,
        )


class FolderRecommendationResultDTO(APIBaseDTO):
    primary: FolderRecommendationDTO
    alternatives: list[FolderRecommendationDTO] = Field(default_factory=list)
    confidence: float

    @classmethod
    def from_model(cls, result: FolderRecommendationResult) -> FolderRecommendationResultDTO:
        return cls(
            primary=FolderRecommendationDTO.from_model(result.primary),
            alternatives=[
                FolderRecommendationDTO.from_model(recommendation)
                for recommendation in result.alternatives
            ],
            confidence=result.confidence,
        )


class RecommendFolderResponse(FolderRecommendationResultDTO):
    @classmethod
    def from_model(cls, result: FolderRecommendationResult) -> RecommendFolderResponse:
        return cls(
            primary=FolderRecommendationDTO.from_model(result.primary),
            alternatives=[
                FolderRecommendationDTO.from_model(recommendation)
                for recommendation in result.alternatives
            ],
            confidence=result.confidence,
        )


class RelatedRecommendationItemDTO(APIBaseDTO):
    score: float
    reason: str
    document: DocumentRecommendationDTO | None = None
    folder: FolderRecommendationDTO | None = None

    @classmethod
    def from_model(cls, item: RelatedRecommendationItem) -> RelatedRecommendationItemDTO:
        return cls(
            score=item.score,
            reason=item.reason,
            document=(
                DocumentRecommendationDTO.from_model(item.document)
                if item.document is not None
                else None
            ),
            folder=(
                FolderRecommendationDTO.from_model(item.folder)
                if item.folder is not None
                else None
            ),
        )


class RelatedRecommendationResultDTO(APIBaseDTO):
    items: list[RelatedRecommendationItemDTO] = Field(default_factory=list)
    confidence: float

    @classmethod
    def from_model(
        cls,
        result: RelatedRecommendationResult,
    ) -> RelatedRecommendationResultDTO:
        return cls(
            items=[RelatedRecommendationItemDTO.from_model(item) for item in result.items],
            confidence=result.confidence,
        )
