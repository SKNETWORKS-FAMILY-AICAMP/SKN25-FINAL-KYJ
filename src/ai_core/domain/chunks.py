from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.common.types import Metadata
from ai_core.domain.folders import IndexedFolder


@dataclass(slots=True)
class DocumentChunk:
    tenant: str
    entity_type: str
    entity_id: str
    version: str
    chunk_id: str
    text: str
    chunk_index: int
    start_offset: int
    end_offset: int
    folder_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)

    @property
    def document_key(self) -> str:
        return f"{self.tenant}:{self.entity_type}:{self.entity_id}"

    @property
    def source_key(self) -> str:
        return f"{self.document_key}:{self.version}"


@dataclass(slots=True)
class RetrievalResult:
    chunk: DocumentChunk
    score: float


@dataclass(slots=True)
class FolderRetrievalResult:
    folder: IndexedFolder
    score: float


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
