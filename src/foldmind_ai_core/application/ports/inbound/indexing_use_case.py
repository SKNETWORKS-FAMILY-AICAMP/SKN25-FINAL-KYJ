from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.domain.indexing.chunks import DocumentChunk
from foldmind_ai_core.domain.reference.documents import SourceDocument
from foldmind_ai_core.domain.reference.folders import SourceFolder
from foldmind_ai_core.domain.retrieval.results import RetrievedFolder


class IndexDocumentUseCasePort(Protocol):
    def execute(self, document: SourceDocument) -> list[DocumentChunk]:
        ...


class DeleteDocumentIndexUseCasePort(Protocol):
    def execute(self, *, document_id: str) -> None:
        ...


class IndexFolderUseCasePort(Protocol):
    def execute(self, folder: SourceFolder) -> RetrievedFolder:
        ...


class DeleteFolderIndexUseCasePort(Protocol):
    def execute(self, *, folder_id: str) -> None:
        ...
