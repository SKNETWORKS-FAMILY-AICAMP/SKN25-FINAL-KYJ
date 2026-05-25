from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.models.retrieval import (
    RetrievalResult,
    RetrievedDocument,
)


@dataclass(slots=True)
class AssistantClarification:
    question: str
    reason: str


@dataclass(slots=True)
class GeneratedTextResult:
    text: str
    citations: list[RetrievalResult] = field(default_factory=list)


@dataclass(slots=True)
class DraftResult:
    draft: str
    citations: list[RetrievalResult] = field(default_factory=list)


@dataclass(slots=True)
class DocumentRecommendation:
    document: RetrievedDocument
    reason: str
    score: float
    evidence: list[RetrievalResult] = field(default_factory=list)


@dataclass(slots=True)
class DocumentRecommendationResult:
    primary: DocumentRecommendation | None = None
    alternatives: list[DocumentRecommendation] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return self.primary.score if self.primary is not None else 0.0


@dataclass(slots=True)
class DocumentSearchResult:
    items: list[DocumentRecommendation] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return max((item.score for item in self.items), default=0.0)


@dataclass(slots=True)
class FolderRecommendation:
    folder_id: str
    reason: str
    score: float


@dataclass(slots=True)
class FolderRecommendationResult:
    primary: FolderRecommendation
    alternatives: list[FolderRecommendation] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return self.primary.score


@dataclass(slots=True)
class RelatedRecommendationResult:
    items: list[DocumentRecommendation | FolderRecommendation] = field(default_factory=list)

    @property
    def documents(self) -> list[DocumentRecommendation]:
        return [
            item
            for item in self.items
            if isinstance(item, DocumentRecommendation)
        ]

    @property
    def folders(self) -> list[FolderRecommendation]:
        return [
            item
            for item in self.items
            if isinstance(item, FolderRecommendation)
        ]

    @property
    def confidence(self) -> float:
        return max((item.score for item in self.items), default=0.0)
