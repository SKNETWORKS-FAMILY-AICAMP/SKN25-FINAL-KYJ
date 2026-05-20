from __future__ import annotations

from pydantic import Field

from foldmind_ai_core.adapters.inbound.http.dtos.documents import RetrievedDocumentDTO
from foldmind_ai_core.adapters.inbound.http.dtos.dto_model import APIDTO
from foldmind_ai_core.adapters.inbound.http.dtos.retrieval import (
    FolderRecommendationDTO,
    RetrievalResultDTO,
)


class AssistantClarificationDTO(APIDTO):
    question: str
    reason: str


class DraftResultDTO(APIDTO):
    draft: str
    citations: list[RetrievalResultDTO] = Field(default_factory=list)


class DocumentRecommendationDTO(APIDTO):
    document: RetrievedDocumentDTO
    reason: str
    score: float
    evidence: list[RetrievalResultDTO] = Field(default_factory=list)


class DocumentRecommendationResultDTO(APIDTO):
    primary: DocumentRecommendationDTO | None = None
    alternatives: list[DocumentRecommendationDTO] = Field(default_factory=list)
    confidence: float


class DocumentSearchItemDTO(APIDTO):
    document: RetrievedDocumentDTO
    score: float
    reason: str
    evidence: list[RetrievalResultDTO] = Field(default_factory=list)


class DocumentSearchResultDTO(APIDTO):
    items: list[DocumentSearchItemDTO] = Field(default_factory=list)
    confidence: float


class FolderRecommendationResultDTO(APIDTO):
    primary: FolderRecommendationDTO
    alternatives: list[FolderRecommendationDTO] = Field(default_factory=list)
    confidence: float


class RelatedRecommendationItemDTO(APIDTO):
    score: float
    reason: str
    document: DocumentRecommendationDTO | None = None
    folder: FolderRecommendationDTO | None = None


class RelatedRecommendationResultDTO(APIDTO):
    items: list[RelatedRecommendationItemDTO] = Field(default_factory=list)
    confidence: float
