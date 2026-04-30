from __future__ import annotations

from pydantic import Field

from ai_core.api.dto.base import APIBaseDTO
from ai_core.api.dto.documents import IndexedDocumentDTO, IndexedFolderDTO, SourceDocumentDTO
from ai_core.api.dto.retrieval import RetrievalResultDTO
from ai_core.application.models.results import (
    DocumentRecommendation,
    DocumentRecommendationResult,
    FolderRecommendation,
    FolderRecommendationResult,
    RelatedRecommendationItem,
    RelatedRecommendationResult,
)
from ai_core.domain.documents import SourceDocument


class RecommendFolderRequest(APIBaseDTO):
    document: SourceDocumentDTO

    def to_model(self) -> SourceDocument:
        return self.document.to_model()


class DocumentRecommendationDTO(APIBaseDTO):
    document: IndexedDocumentDTO
    reason: str
    score: float
    evidence: list[RetrievalResultDTO] = Field(default_factory=list)

    @classmethod
    def from_model(cls, recommendation: DocumentRecommendation) -> DocumentRecommendationDTO:
        return cls(
            document=IndexedDocumentDTO.from_model(recommendation.document),
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
    folder: IndexedFolderDTO
    reason: str
    score: float

    @classmethod
    def from_model(cls, recommendation: FolderRecommendation) -> FolderRecommendationDTO:
        return cls(
            folder=IndexedFolderDTO.from_model(recommendation.folder),
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
    pass


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
