from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.models.search import RequestContext, SearchScope
from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.document_signals import DocumentSignalEvidence
from foldmind_ai_core.core.domain.models.document_sources import DocumentSourceState
from foldmind_ai_core.core.domain.models.folder_sources import SourceFolder
from foldmind_ai_core.shared.types import Metadata


@dataclass(slots=True)
class RetrievalQuery:
    text: str
    request_context: RequestContext
    scope: SearchScope | None = None


@dataclass(slots=True)
class FolderSearchQuery:
    tenant: str
    text: str
    scope: SearchScope | None = None
    excluded_folder_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentTitleKeywordMatch:
    source: DocumentSourceState
    score: float


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
    evidence: tuple[DocumentSignalEvidence, ...] = ()
    confidence: float | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class SignalRetrievalResult:
    signal: RetrievedSignal
    score: float


@dataclass(frozen=True, slots=True)
class FolderRetrievalResult:
    folder: SourceFolder
    score: float
    reason: str = ""


@dataclass(slots=True)
class RelatedRetrievalResult:
    items: list[RetrievalResult | FolderRetrievalResult] = field(default_factory=list)

    @property
    def documents(self) -> list[RetrievalResult]:
        return [
            item
            for item in self.items
            if isinstance(item, RetrievalResult)
        ]

    @property
    def folders(self) -> list[FolderRetrievalResult]:
        return [
            item
            for item in self.items
            if isinstance(item, FolderRetrievalResult)
        ]

    @property
    def confidence(self) -> float:
        return max((item.score for item in self.items), default=0.0)
