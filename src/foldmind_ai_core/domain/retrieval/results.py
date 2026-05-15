from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.shared.types import Metadata


@dataclass(slots=True)
class RetrievalResult:
    chunk: DocumentChunk
    score: float


@dataclass(frozen=True, slots=True)
class RetrievedDocument:
    tenant: str
    document_type: str
    document_id: str
    source_version: str
    snippet: str = ""
    profile_version: str | None = None
    profile_schema_version: str = ""
    concept_ids: tuple[str, ...] = ()
    profile_confidence: float | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class DocumentRetrievalResult:
    document: RetrievedDocument
    score: float


@dataclass(frozen=True, slots=True)
class RetrievedFolder:
    tenant: str
    folder_id: str
    source_version: str


@dataclass(frozen=True, slots=True)
class FolderRetrievalResult:
    folder: RetrievedFolder
    score: float
    reason: str = ""


@dataclass(slots=True)
class RelatedRetrievalItem:
    target: RetrievalResult | FolderRetrievalResult

    @property
    def score(self) -> float:
        return self.target.score

    @property
    def document(self) -> RetrievalResult | None:
        if isinstance(self.target, RetrievalResult):
            return self.target
        return None

    @property
    def folder(self) -> FolderRetrievalResult | None:
        if isinstance(self.target, FolderRetrievalResult):
            return self.target
        return None


@dataclass(slots=True)
class RelatedRetrievalResult:
    items: list[RelatedRetrievalItem] = field(default_factory=list)

    @property
    def documents(self) -> list[RetrievalResult]:
        return [item.document for item in self.items if item.document is not None]

    @property
    def folders(self) -> list[FolderRetrievalResult]:
        return [item.folder for item in self.items if item.folder is not None]

    @property
    def confidence(self) -> float:
        return self.items[0].score if self.items else 0.0
