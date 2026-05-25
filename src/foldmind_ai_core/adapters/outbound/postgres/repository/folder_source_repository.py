from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from foldmind_ai_core.adapters.outbound.postgres.mappers.indexing import (
    folder_source_row_from_domain,
    source_folder_from_row,
)
from foldmind_ai_core.adapters.outbound.postgres.policies.retention_policy import (
    PurgeAfterPolicy,
)
from foldmind_ai_core.adapters.outbound.postgres.store.folder_source_store import (
    FolderSourceStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.tenant_storage_scope_store import (
    TenantStorageScopeStore,
)
from foldmind_ai_core.core.domain.models.folder_sources import (
    FolderSourceIdentity,
    SourceFolder,
)


@dataclass(slots=True)
class FolderSourceRepository:
    tenants: TenantStorageScopeStore
    folder_sources: FolderSourceStore
    purge_after_policy: PurgeAfterPolicy = field(default_factory=PurgeAfterPolicy)

    async def upsert_folder_source(
        self,
        folder: SourceFolder,
    ) -> bool:
        await self.tenants.upsert_tenant_scope(folder.tenant)
        await self.folder_sources.upsert_folder_source(
            folder_source_row_from_domain(folder)
        )
        return await self.folder_sources.folder_source_version_is_current(
            tenant=folder.tenant,
            folder_id=folder.folder_id,
            source_version=folder.source_version,
        )

    async def get_current_folder_source(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> SourceFolder | None:
        row = await self.folder_sources.current_folder_source_row(
            tenant=tenant,
            folder_id=folder_id,
        )
        return source_folder_from_row(row) if row is not None else None

    async def ancestor_folder_ids(
        self,
        *,
        tenant: str,
        folder_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        return await self.folder_sources.ancestor_folder_ids(
            tenant=tenant,
            folder_ids=folder_ids,
        )

    async def active_folder_ids_in_subtree(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> tuple[str, ...]:
        return await self.folder_sources.active_folder_ids_in_subtree(
            tenant=tenant,
            folder_id=folder_id,
        )

    async def folder_identity_for_delete(
        self,
        folder_id: str,
    ) -> FolderSourceIdentity | None:
        row = await self.folder_sources.folder_source_row_for_delete(folder_id)
        if row is None:
            return None
        return FolderSourceIdentity(
            tenant=row.tenant_id,
            folder_id=row.folder_id,
            source_version=row.source_version,
        )

    async def mark_folder_source_deleted(
        self,
        *,
        tenant: str,
        folder_id: str,
    ) -> None:
        await self.folder_sources.mark_folder_source_deleted(
            tenant=tenant,
            folder_id=folder_id,
            purge_after=self.purge_after_policy.purge_after(),
        )

    async def search_names_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        folder_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
    ) -> tuple[tuple[SourceFolder, float], ...]:
        rows = await self.folder_sources.keyword_name_rows(
            tenant=tenant,
            query_text=query_text,
            top_k=top_k,
            folder_ids=folder_ids,
            created_at=created_at,
            updated_at=updated_at,
        )
        return tuple((source_folder_from_row(row), score) for row, score in rows)

    async def search_descriptions_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        folder_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
    ) -> tuple[tuple[SourceFolder, float], ...]:
        rows = await self.folder_sources.keyword_description_rows(
            tenant=tenant,
            query_text=query_text,
            top_k=top_k,
            folder_ids=folder_ids,
            created_at=created_at,
            updated_at=updated_at,
        )
        return tuple((source_folder_from_row(row), score) for row, score in rows)
