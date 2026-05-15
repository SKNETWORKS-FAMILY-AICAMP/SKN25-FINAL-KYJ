from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.domain.indexing.projection_events import (
    DocumentDeletedProjectionEvent,
    DocumentIndexedProjectionEvent,
    FolderDeletedProjectionEvent,
    FolderIndexedProjectionEvent,
)


class HandleDocumentChunkVectorIndexedProjectionUseCasePort(Protocol):
    def handle(self, event: DocumentIndexedProjectionEvent) -> None:
        ...


class HandleDocumentChunkVectorDeletedProjectionUseCasePort(Protocol):
    def handle(self, event: DocumentDeletedProjectionEvent) -> None:
        ...


class HandleDocumentVectorIndexedProjectionUseCasePort(Protocol):
    def handle(self, event: DocumentIndexedProjectionEvent) -> None:
        ...


class HandleDocumentVectorDeletedProjectionUseCasePort(Protocol):
    def handle(self, event: DocumentDeletedProjectionEvent) -> None:
        ...


class HandleDocumentGraphIndexedProjectionUseCasePort(Protocol):
    def handle(self, event: DocumentIndexedProjectionEvent) -> None:
        ...


class HandleDocumentGraphDeletedProjectionUseCasePort(Protocol):
    def handle(self, event: DocumentDeletedProjectionEvent) -> None:
        ...


class HandleFolderVectorIndexedProjectionUseCasePort(Protocol):
    def handle(self, event: FolderIndexedProjectionEvent) -> None:
        ...


class HandleFolderVectorDeletedProjectionUseCasePort(Protocol):
    def handle(self, event: FolderDeletedProjectionEvent) -> None:
        ...


class HandleFolderGraphIndexedProjectionUseCasePort(Protocol):
    def handle(self, event: FolderIndexedProjectionEvent) -> None:
        ...


class HandleFolderGraphDeletedProjectionUseCasePort(Protocol):
    def handle(self, event: FolderDeletedProjectionEvent) -> None:
        ...
