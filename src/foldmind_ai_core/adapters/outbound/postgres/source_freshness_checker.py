from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.postgres.client import (
    PostgresSessionProvider,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_index_record_store import (
    DocumentIndexRecordStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_source_store import (
    DocumentSourceStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.folder_index_record_store import (
    FolderIndexRecordStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.folder_source_store import (
    FolderSourceStore,
)


@dataclass(slots=True)
class PostgresSourceFreshnessChecker:
    sessions: PostgresSessionProvider

    def close(self) -> object:
        close = getattr(self.sessions, "close", None)
        if close is None:
            return None
        return close()

    async def is_current_document_folder_relation_snapshot(
        self,
        *,
        tenant: str,
        document_id: str,
        source_version: str,
    ) -> bool:
        async with self.sessions.session() as session:
            return await DocumentSourceStore(session).document_source_version_is_current(
                tenant=tenant,
                document_id=document_id,
                source_version=source_version,
            )

    async def is_current_document_index_input_digest(
        self,
        *,
        tenant: str,
        document_id: str,
        document_index_input_digest: str,
    ) -> bool:
        async with self.sessions.session() as session:
            source_row = await DocumentSourceStore(session).current_document_source_row(
                tenant=tenant,
                document_id=document_id,
            )
            if source_row is None:
                return False
            return await DocumentIndexRecordStore(
                session,
            ).document_index_input_digest_is_current(
                document_id=document_id,
                document_index_input_digest=document_index_input_digest,
            )

    async def is_current_document_signal_input_digest(
        self,
        *,
        tenant: str,
        document_id: str,
        document_signal_input_digest: str,
        signal_generation_version: str,
    ) -> bool:
        async with self.sessions.session() as session:
            source_row = await DocumentSourceStore(session).current_document_source_row(
                tenant=tenant,
                document_id=document_id,
            )
            if source_row is None:
                return False
            return await DocumentIndexRecordStore(
                session,
            ).document_signal_input_digest_is_current(
                document_id=document_id,
                document_signal_input_digest=document_signal_input_digest,
                signal_generation_version=signal_generation_version,
            )

    async def is_current_folder_index_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
        folder_index_input_digest: str,
    ) -> bool:
        async with self.sessions.session() as session:
            source_row = await FolderSourceStore(session).current_folder_source_row(
                tenant=tenant,
                folder_id=folder_id,
            )
            if source_row is None:
                return False
            return await FolderIndexRecordStore(
                session,
            ).folder_index_input_digest_is_current(
                folder_id=folder_id,
                folder_index_input_digest=folder_index_input_digest,
            )

    async def is_current_folder_signal_input_digest(
        self,
        *,
        tenant: str,
        folder_id: str,
        folder_signal_input_digest: str,
    ) -> bool:
        async with self.sessions.session() as session:
            source_row = await FolderSourceStore(session).current_folder_source_row(
                tenant=tenant,
                folder_id=folder_id,
            )
            if source_row is None:
                return False
            current_digest = await FolderIndexRecordStore(
                session,
            ).current_folder_signal_input_digest(
                folder_id=folder_id,
            )
            return current_digest == folder_signal_input_digest
