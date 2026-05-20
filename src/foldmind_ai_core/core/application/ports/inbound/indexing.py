from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.commands.indexing import (
    DeleteDocumentIndexCommand,
    DeleteFolderIndexCommand,
    IndexDocumentCommand,
    IndexFolderCommand,
    UpdateDocumentFolderRelationsCommand,
)
from foldmind_ai_core.core.application.results.indexing import (
    IndexDocumentResult,
    IndexFolderResult,
)


class IndexDocumentInboundPort(Protocol):
    def execute(self, command: IndexDocumentCommand) -> IndexDocumentResult:
        ...


class DeleteDocumentIndexInboundPort(Protocol):
    def execute(self, command: DeleteDocumentIndexCommand) -> None:
        ...


class UpdateDocumentFolderRelationsInboundPort(Protocol):
    def execute(self, command: UpdateDocumentFolderRelationsCommand) -> None:
        ...


class IndexFolderInboundPort(Protocol):
    def execute(self, command: IndexFolderCommand) -> IndexFolderResult:
        ...


class DeleteFolderIndexInboundPort(Protocol):
    def execute(self, command: DeleteFolderIndexCommand) -> None:
        ...
