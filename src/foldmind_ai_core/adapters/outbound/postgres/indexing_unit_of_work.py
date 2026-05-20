from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from foldmind_ai_core.adapters.outbound.postgres.client import PostgresClient
from foldmind_ai_core.adapters.outbound.postgres.outbox_repository import (
    PostgresOutboxRepository,
)
from foldmind_ai_core.adapters.outbound.postgres.index_repository import (
    PostgresIndexRepository,
)
from foldmind_ai_core.core.domain.models.indexing.chunks import DocumentChunk
from foldmind_ai_core.core.domain.models.indexing.outbox import OutboxEvent
from foldmind_ai_core.core.application.models.indexing import (
    DeletedDocumentIdentity,
    DeletedFolderIdentity,
    DocumentIndexChange,
    FolderIndexChange,
    FolderRelationChange,
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


@dataclass(slots=True)
class PostgresIndexingUnitOfWork:
    client: PostgresClient
    index_repository: PostgresIndexRepository
    outbox_repository: PostgresOutboxRepository

    @contextmanager
    def transaction(self) -> Iterator[PostgresIndexingTransaction]:
        with self.client.transaction() as conn:
            yield PostgresIndexingTransaction(
                conn=conn,
                index_repository=self.index_repository,
                outbox_repository=self.outbox_repository,
            )


@dataclass(slots=True)
class PostgresIndexingTransaction:
    conn: Any
    index_repository: PostgresIndexRepository
    outbox_repository: PostgresOutboxRepository

    def upsert_document_index(
        self,
        *,
        document: SourceDocument,
        chunks: tuple[DocumentChunk, ...],
        profile: DocumentProfile,
        signals: tuple[DocumentSignal, ...],
    ) -> DocumentIndexChange:
        return self.index_repository.upsert_document_index_with_connection(
            self.conn,
            document=document,
            chunks=chunks,
            profile=profile,
            signals=signals,
        )

    def mark_document_deleted(
        self,
        *,
        document_id: str,
    ) -> DeletedDocumentIdentity | None:
        return self.index_repository.mark_document_deleted_with_connection(
            self.conn,
            document_id=document_id,
        )

    def replace_document_folder_relation_snapshot(
        self,
        *,
        snapshot: SourceDocumentFolderRelationSnapshot,
    ) -> FolderRelationChange:
        return self.index_repository.replace_document_folder_relation_snapshot_with_connection(
            self.conn,
            snapshot=snapshot,
        )

    def upsert_folder_index(
        self,
        *,
        folder: SourceFolder,
    ) -> FolderIndexChange:
        return self.index_repository.upsert_folder_index_with_connection(
            self.conn,
            folder=folder,
        )

    def current_folder_index_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> str | None:
        return self.index_repository.current_folder_index_input_digest_with_connection(
            self.conn,
            tenant=tenant,
            folder_id=folder_id,
        )

    def replace_folder_signals(
        self,
        *,
        folder: SourceFolder,
        signals: tuple[FolderSignal, ...],
        expected_index_input_digest: str,
        signal_generation_version: str,
    ) -> FolderSignalRefreshCommit:
        return self.index_repository.replace_folder_signals_with_connection(
            self.conn,
            folder=folder,
            signals=signals,
            expected_index_input_digest=expected_index_input_digest,
            signal_generation_version=signal_generation_version,
        )

    def mark_folder_deleted(self, *, folder_id: str) -> DeletedFolderIdentity | None:
        return self.index_repository.mark_folder_deleted_with_connection(
            self.conn,
            folder_id=folder_id,
        )

    def append_outbox_event(self, event: OutboxEvent) -> None:
        self.outbox_repository.append_with_connection(self.conn, event)
