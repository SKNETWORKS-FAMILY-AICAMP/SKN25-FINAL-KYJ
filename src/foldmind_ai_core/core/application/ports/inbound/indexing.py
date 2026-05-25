from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.models.indexing import (
    DeleteDocumentIndexCommand,
    DeleteFolderIndexCommand,
    IndexDocumentCommand,
)
from foldmind_ai_core.core.application.models.indexing import IndexDocumentResult
from foldmind_ai_core.core.domain.models.folder_sources import (
    FolderSourceIdentity,
    SourceFolder,
)


class DocumentIndexingServicePort(Protocol):
    async def index_document(
        self,
        command: IndexDocumentCommand,
    ) -> IndexDocumentResult:
        ...

    async def delete_document(
        self,
        command: DeleteDocumentIndexCommand,
    ) -> None:
        ...


class FolderIndexingServicePort(Protocol):
    async def index_folder(
        self,
        folder: SourceFolder,
    ) -> FolderSourceIdentity:
        ...

    async def delete_folder(
        self,
        command: DeleteFolderIndexCommand,
    ) -> None:
        ...
