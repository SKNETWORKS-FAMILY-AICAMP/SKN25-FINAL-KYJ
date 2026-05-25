from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from .client import PostgresSessionProvider
from .policies.retention_policy import PurgeAfterPolicy
from .repository.document_projection_repository import (
    DocumentProjectionRepository,
)
from .repository.document_relation_repository import (
    DocumentRelationRepository,
)
from .repository.document_source_repository import (
    DocumentSourceRepository,
)
from .repository.folder_projection_repository import (
    FolderProjectionRepository,
)
from .repository.folder_source_repository import (
    FolderSourceRepository,
)
from .repository.outbox_repository import OutboxRepository
from .store.document_chunk_store import DocumentChunkStore
from .store.document_folder_relation_store import DocumentFolderRelationStore
from .store.document_index_record_store import DocumentIndexRecordStore
from .store.document_signal_store import DocumentSignalStore
from .store.document_source_store import DocumentSourceStore
from .store.folder_index_record_store import FolderIndexRecordStore
from .store.folder_signal_store import FolderSignalStore
from .store.folder_source_store import FolderSourceStore
from .store.outbox_store import OutboxEventStore
from .store.tenant_storage_scope_store import TenantStorageScopeStore


@dataclass(slots=True)
class PostgresIndexingWriteSessionProvider:
    sessions: PostgresSessionProvider
    purge_after_policy: PurgeAfterPolicy = field(default_factory=PurgeAfterPolicy)

    def close(self) -> object:
        close = getattr(self.sessions, "close", None)
        if close is None:
            return None
        return close()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[PostgresIndexingWriteSession]:
        async with self.sessions.transaction() as session:
            document_sources = DocumentSourceStore(session)
            folder_sources = FolderSourceStore(session)
            tenants = TenantStorageScopeStore(session)
            yield PostgresIndexingWriteSession(
                document_sources=DocumentSourceRepository(
                    tenants=tenants,
                    document_sources=document_sources,
                    purge_after_policy=self.purge_after_policy,
                ),
                folder_sources=FolderSourceRepository(
                    tenants=tenants,
                    folder_sources=folder_sources,
                    purge_after_policy=self.purge_after_policy,
                ),
                document_projections=DocumentProjectionRepository(
                    document_sources=document_sources,
                    document_index_records=DocumentIndexRecordStore(session),
                    document_chunks=DocumentChunkStore(session),
                    document_signals=DocumentSignalStore(session),
                    purge_after_policy=self.purge_after_policy,
                ),
                document_relations=DocumentRelationRepository(
                    document_folder_relations=DocumentFolderRelationStore(session),
                ),
                folder_projections=FolderProjectionRepository(
                    folder_sources=folder_sources,
                    folder_index_records=FolderIndexRecordStore(session),
                    folder_signals=FolderSignalStore(session),
                    purge_after_policy=self.purge_after_policy,
                ),
                outbox=OutboxRepository(outbox_events=OutboxEventStore(session)),
            )


@dataclass(slots=True)
class PostgresIndexingWriteSession:
    document_sources: DocumentSourceRepository
    folder_sources: FolderSourceRepository
    document_projections: DocumentProjectionRepository
    document_relations: DocumentRelationRepository
    folder_projections: FolderProjectionRepository
    outbox: OutboxRepository
