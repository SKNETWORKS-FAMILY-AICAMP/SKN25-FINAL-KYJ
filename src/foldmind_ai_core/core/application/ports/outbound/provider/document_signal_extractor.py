from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.document_chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.document_sources import SourceDocument
from foldmind_ai_core.core.application.models.indexing import DocumentSignalExtraction


class DocumentSignalExtractor(Protocol):
    async def extract(
        self,
        document: SourceDocument,
        chunks: list[DocumentChunk],
    ) -> DocumentSignalExtraction:
        ...
