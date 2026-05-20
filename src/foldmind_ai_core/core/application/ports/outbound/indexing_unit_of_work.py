from __future__ import annotations

from types import TracebackType
from typing import Protocol

from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.application.models.indexing import (
    DeletedDocumentIdentity,
    DeletedFolderIdentity,
    SourceDocumentFolderRelationSnapshot,
)
from foldmind_ai_core.core.domain.models.profiling import (
    DocumentProfile,
    DocumentSignal,
    FolderSignal,
)
from foldmind_ai_core.core.domain.models.reference.documents import SourceDocument
from foldmind_ai_core.core.domain.models.reference.folders import SourceFolder


class IndexingTransaction(Protocol):
    def upsert_document_index(
        self,
        *,
        document: SourceDocument,
        chunks: tuple[DocumentChunk, ...],
        profile: DocumentProfile,
        signals: tuple[DocumentSignal, ...],
    ) -> None:
        ...

    def mark_document_deleted(
        self,
        *,
        document_id: str,
    ) -> DeletedDocumentIdentity | None:
        ...

    def replace_document_folder_relation_snapshot(
        self,
        *,
        snapshot: SourceDocumentFolderRelationSnapshot,
    ) -> bool:
        ...

    def upsert_folder_index(
        self,
        *,
        folder: SourceFolder,
        signals: tuple[FolderSignal, ...] = (),
    ) -> None:
        ...

    def mark_folder_deleted(
        self,
        *,
        folder_id: str,
    ) -> DeletedFolderIdentity | None:
        ...

    def append_outbox_event(self, event: OutboxEvent) -> None:
        ...


class IndexingTransactionScope(Protocol):
    def __enter__(self) -> IndexingTransaction:
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        ...


class IndexingUnitOfWork(Protocol):
    def transaction(self) -> IndexingTransactionScope:
        ...
