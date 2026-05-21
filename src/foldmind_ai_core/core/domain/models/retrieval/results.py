from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.shared.types import Metadata


@dataclass(slots=True)
class RetrievalResult:
    chunk: DocumentChunk
    score: float


@dataclass(frozen=True, slots=True)
class RetrievedDocument:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    created_at: str = ""
    updated_at: str = ""
    snippet: str = ""
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class DocumentRetrievalResult:
    document: RetrievedDocument
    score: float


@dataclass(frozen=True, slots=True)
class RetrievedSignalEvidence:
    chunk_id: str
    quote: str
    start_offset: int | None = None
    end_offset: int | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievedSignal:
    signal_id: str
    tenant: str
    document_type: str | None
    document_id: str | None
    signal_type: str
    signal_key: str
    text: str
    source_version: str
    owner_kind: str = "document"
    folder_id: str | None = None
    related_document_id: str | None = None
    evidence: tuple[RetrievedSignalEvidence, ...] = ()
    confidence: float | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class SignalRetrievalResult:
    signal: RetrievedSignal
    score: float


@dataclass(frozen=True, slots=True)
class RetrievedFolder:
    tenant: str
    folder_id: str
    source_version: str
    created_at: str = ""
    updated_at: str = ""
    name: str = ""
    path: str | None = None
    parent_folder_id: str | None = None
    description: str = ""
    metadata: Metadata = field(default_factory=dict)


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
        return [
            document
            for item in self.items
            if (document := item.document) is not None
        ]

    @property
    def folders(self) -> list[FolderRetrievalResult]:
        return [
            folder
            for item in self.items
            if (folder := item.folder) is not None
        ]

    @property
    def confidence(self) -> float:
        return max((item.score for item in self.items), default=0.0)
