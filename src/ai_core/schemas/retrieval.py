from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_core.schemas.chunk import DocumentChunk
from ai_core.schemas.source_folder import SourceFolder


@dataclass(slots=True)
class AIQuery:
    text: str
    entity_type: str | None = None
    entity_id: str | None = None
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentScope:
    entity_type: str | None = None
    entity_id: str | None = None


@dataclass(slots=True)
class RetrievalResult:
    chunk: DocumentChunk
    score: float


@dataclass(slots=True)
class FolderRetrievalResult:
    folder: SourceFolder
    score: float


@dataclass(slots=True)
class RelatedRetrievalResult:
    documents: list[RetrievalResult] = field(default_factory=list)
    folders: list[FolderRetrievalResult] = field(default_factory=list)
