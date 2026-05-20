from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.domain.models.retrieval.results import RetrievalResult, RetrievedDocument


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
class DocumentSearchItem:
    document: RetrievedDocument
    score: float
    reason: str
    evidence: list[RetrievalResult] = field(default_factory=list)


@dataclass(slots=True)
class DocumentSearchResult:
    items: list[DocumentSearchItem] = field(default_factory=list)

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
class RelatedRecommendationItem:
    target: DocumentRecommendation | FolderRecommendation

    @property
    def score(self) -> float:
        return self.target.score

    @property
    def reason(self) -> str:
        return self.target.reason

    @property
    def document(self) -> DocumentRecommendation | None:
        if isinstance(self.target, DocumentRecommendation):
            return self.target
        return None

    @property
    def folder(self) -> FolderRecommendation | None:
        if isinstance(self.target, FolderRecommendation):
            return self.target
        return None


@dataclass(slots=True)
class RelatedRecommendationResult:
    items: list[RelatedRecommendationItem] = field(default_factory=list)

    @property
    def documents(self) -> list[DocumentRecommendation]:
        return [
            document
            for item in self.items
            if (document := item.document) is not None
        ]

    @property
    def folders(self) -> list[FolderRecommendation]:
        return [
            folder
            for item in self.items
            if (folder := item.folder) is not None
        ]

    @property
    def confidence(self) -> float:
        return max((item.score for item in self.items), default=0.0)
