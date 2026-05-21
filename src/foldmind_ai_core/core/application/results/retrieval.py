from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.shared.types import Metadata


@dataclass(frozen=True, slots=True)
class RetrievedChunkResult:
    tenant: str
    document_type: str | None
    document_id: str
    source_version: str
    document_index_input_digest: str
    created_at: str
    updated_at: str
    chunk_id: str
    chunk_index: int
    chunking_version: str
    text: str
    text_hash: str
    start_offset: int
    end_offset: int
    embedding_model: str
    embedding_version: str
    index_schema_version: str
    score: float
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SearchDocumentsResult:
    results: tuple[RetrievedChunkResult, ...]


@dataclass(frozen=True, slots=True)
class RetrievedSignalEvidenceResult:
    chunk_id: str
    quote: str
    start_offset: int | None = None
    end_offset: int | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RetrievedSignalResult:
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
    evidence: tuple[RetrievedSignalEvidenceResult, ...] = ()
    confidence: float | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SignalSearchResultItem:
    signal: RetrievedSignalResult
    score: float


@dataclass(frozen=True, slots=True)
class SearchSignalsResult:
    results: tuple[SignalSearchResultItem, ...]


@dataclass(frozen=True, slots=True)
class RetrievedFolderResult:
    tenant: str
    folder_id: str
    source_version: str
    created_at: str = ""
    updated_at: str = ""
    name: str = ""
    path: str | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class FolderSearchResultItem:
    folder: RetrievedFolderResult
    score: float
    reason: str = ""


@dataclass(frozen=True, slots=True)
class SearchFoldersResult:
    results: tuple[FolderSearchResultItem, ...]


@dataclass(frozen=True, slots=True)
class FolderRecommendationResultItem:
    folder_id: str
    reason: str
    score: float


@dataclass(frozen=True, slots=True)
class RecommendFolderResult:
    primary: FolderRecommendationResultItem
    alternatives: tuple[FolderRecommendationResultItem, ...] = ()

    @property
    def confidence(self) -> float:
        return self.primary.score
