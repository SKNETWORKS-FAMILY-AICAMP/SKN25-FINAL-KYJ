from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentSignalExtraction,
    FolderSignalExtraction,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder


class DocumentSignalExtractor(Protocol):
    def profile(
        self,
        document: SourceDocument,
        chunks: list[DocumentChunk],
    ) -> DocumentSignalExtraction:
        ...


class FolderSignalExtractor(Protocol):
    def evaluate(
        self,
        folder: SourceFolder,
        member_documents: tuple[SourceDocument, ...],
    ) -> FolderSignalExtraction:
        ...
