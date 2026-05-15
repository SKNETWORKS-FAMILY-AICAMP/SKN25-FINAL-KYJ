from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.profiling.models import DocumentProfile
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.reference.folders import SourceFolder


@dataclass(frozen=True, slots=True)
class DocumentIndexedProjectionEvent:
    document: SourceDocument
    chunks: tuple[DocumentChunk, ...]
    profile: DocumentProfile


@dataclass(frozen=True, slots=True)
class DocumentDeletedProjectionEvent:
    document_id: str


@dataclass(frozen=True, slots=True)
class FolderIndexedProjectionEvent:
    folder: SourceFolder


@dataclass(frozen=True, slots=True)
class FolderDeletedProjectionEvent:
    folder_id: str


ProjectionEvent = (
    DocumentIndexedProjectionEvent
    | DocumentDeletedProjectionEvent
    | FolderIndexedProjectionEvent
    | FolderDeletedProjectionEvent
)
