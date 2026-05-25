from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.postgres.client import PostgresSessionProvider
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    document_projection_repository as document_projections,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    document_relation_repository as document_relations,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    document_source_repository as document_sources,
)
from foldmind_ai_core.adapters.outbound.postgres.repository import (
    folder_source_repository as folder_sources,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_chunk_store import (
    DocumentChunkStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_folder_relation_store import (
    DocumentFolderRelationStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_index_record_store import (
    DocumentIndexRecordStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_signal_store import (
    DocumentSignalStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_source_store import (
    DocumentSourceStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.folder_source_store import (
    FolderSourceStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.tenant_storage_scope_store import (
    TenantStorageScopeStore,
)


@dataclass(slots=True)
class PostgresRetrievalReadSessionProvider:
    sessions: PostgresSessionProvider

    def close(self) -> object:
        close = getattr(self.sessions, "close", None)
        if close is None:
            return None
        return close()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[PostgresRetrievalReadSession]:
        async with self.sessions.session() as session:
            document_source_store = DocumentSourceStore(session)
            document_chunk_store = DocumentChunkStore(session)
            document_folder_relation_store = DocumentFolderRelationStore(session)
            folder_source_store = FolderSourceStore(session)
            yield PostgresRetrievalReadSession(
                document_sources=document_sources.DocumentSourceRepository(
                    tenants=TenantStorageScopeStore(session),
                    document_sources=document_source_store,
                ),
                document_projections=document_projections.DocumentProjectionRepository(
                    document_sources=document_source_store,
                    document_index_records=DocumentIndexRecordStore(session),
                    document_chunks=document_chunk_store,
                    document_signals=DocumentSignalStore(session),
                ),
                document_relations=document_relations.DocumentRelationRepository(
                    document_folder_relations=document_folder_relation_store,
                ),
                folder_sources=folder_sources.FolderSourceRepository(
                    tenants=TenantStorageScopeStore(session),
                    folder_sources=folder_source_store,
                ),
            )


@dataclass(slots=True)
class PostgresRetrievalReadSession:
    document_sources: document_sources.DocumentSourceRepository
    document_projections: document_projections.DocumentProjectionRepository
    document_relations: document_relations.DocumentRelationRepository
    folder_sources: folder_sources.FolderSourceRepository
