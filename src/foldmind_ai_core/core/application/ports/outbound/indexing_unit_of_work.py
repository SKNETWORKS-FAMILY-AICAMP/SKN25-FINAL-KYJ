from __future__ import annotations

from types import TracebackType
from typing import Protocol

from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.application.models.indexing import (
    DeletedDocumentIdentity,
    DeletedFolderIdentity,
    DocumentIndexChange,
    FolderIndexChange,
    FolderRelationChange,
    FolderSignalInvalidation,
    FolderSignalRefreshCommit,
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
    ) -> DocumentIndexChange:
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
    ) -> FolderRelationChange:
        ...

    def upsert_folder_index(
        self,
        *,
        folder: SourceFolder,
    ) -> FolderIndexChange:
        ...

    def current_folder_signal_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> str | None:
        ...

    def replace_folder_signals(
        self,
        *,
        folder: SourceFolder,
        signals: tuple[FolderSignal, ...],
        expected_folder_signal_input_digest: str,
        signal_generation_version: str,
    ) -> FolderSignalRefreshCommit:
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
