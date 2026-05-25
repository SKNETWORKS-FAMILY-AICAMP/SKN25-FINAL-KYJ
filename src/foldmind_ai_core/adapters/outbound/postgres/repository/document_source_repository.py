from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from foldmind_ai_core.adapters.outbound.postgres.mappers.document_source import (
    document_source_state_from_row,
)
from foldmind_ai_core.adapters.outbound.postgres.mappers.indexing import (
    document_source_row_from_domain,
)
from foldmind_ai_core.adapters.outbound.postgres.policies.retention_policy import (
    PurgeAfterPolicy,
)
from foldmind_ai_core.adapters.outbound.postgres.store.document_source_store import (
    DocumentSourceStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.tenant_storage_scope_store import (
    TenantStorageScopeStore,
)
from foldmind_ai_core.core.domain.models.document_sources import (
    DocumentSourceIdentity,
    DocumentSourceState,
    SourceDocument,
)
from foldmind_ai_core.shared.types import Metadata


@dataclass(slots=True)
class DocumentSourceRepository:
    tenants: TenantStorageScopeStore
    document_sources: DocumentSourceStore
    purge_after_policy: PurgeAfterPolicy = field(default_factory=PurgeAfterPolicy)

    async def upsert_document_source(
        self,
        document: SourceDocument,
    ) -> bool:
        await self.tenants.upsert_tenant_scope(document.tenant)
        source_row = document_source_row_from_domain(document)
        await self.document_sources.upsert_document_source(source_row)
        return await self.document_sources.document_source_is_current(
            tenant=document.tenant,
            document_id=document.document_id,
            source_version=document.source_version,
            content_digest=source_row.content_digest,
        )

    async def get_current_document_source(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> DocumentSourceState | None:
        row = await self.document_sources.current_document_source_row(
            tenant=tenant,
            document_id=document_id,
        )
        if row is None:
            return None
        return document_source_state_from_row(tenant=tenant, row=row)

    async def current_document_source_identity_for_update(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> DocumentSourceIdentity | None:
        source_version = await (
            self.document_sources.current_document_source_version_for_update(
                tenant=tenant,
                document_id=document_id,
            )
        )
        if source_version is None:
            return None
        return DocumentSourceIdentity(
            tenant=tenant,
            document_id=document_id,
            source_version=source_version,
        )

    async def get_current_document_sources(
        self,
        *,
        tenant: str,
        document_ids: tuple[str, ...],
    ) -> tuple[DocumentSourceState, ...]:
        rows = await self.document_sources.current_document_source_rows(
            tenant=tenant,
            document_ids=document_ids,
        )
        return tuple(
            document_source_state_from_row(tenant=tenant, row=row)
            for row in rows
        )

    async def document_identity_for_delete(
        self,
        document_id: str,
    ) -> DocumentSourceIdentity | None:
        row = await self.document_sources.document_source_row_for_delete(document_id)
        if row is None:
            return None
        return DocumentSourceIdentity(
            tenant=row.tenant_id,
            document_id=row.document_id,
            source_version=row.source_version,
        )

    async def mark_document_source_deleted(
        self,
        *,
        tenant: str,
        document_id: str,
    ) -> None:
        await self.document_sources.mark_document_source_deleted(
            tenant=tenant,
            document_id=document_id,
            purge_after=self.purge_after_policy.purge_after(),
        )

    async def document_ids_for_scope(
        self,
        *,
        tenant: str,
        document_type: str | None,
        document_id: str | None,
        document_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
        metadata_filter: Metadata | None,
    ) -> tuple[str, ...]:
        return await self.document_sources.current_document_ids(
            tenant=tenant,
            document_type=document_type,
            document_id=document_id,
            document_ids=document_ids,
            created_at=created_at,
            updated_at=updated_at,
            metadata_filter=metadata_filter,
        )

    async def search_titles_by_keyword(
        self,
        *,
        tenant: str,
        query_text: str,
        top_k: int,
        document_type: str | None,
        document_id: str | None,
        document_ids: tuple[str, ...],
        created_at: datetime | None,
        updated_at: datetime | None,
        metadata_filter: Metadata | None,
    ) -> tuple[tuple[DocumentSourceState, float], ...]:
        rows = await self.document_sources.keyword_title_rows(
            tenant=tenant,
            query_text=query_text,
            top_k=top_k,
            document_type=document_type,
            document_id=document_id,
            document_ids=document_ids,
            created_at=created_at,
            updated_at=updated_at,
            metadata_filter=metadata_filter,
        )
        return tuple(
            (document_source_state_from_row(tenant=tenant, row=row), score)
            for row, score in rows
        )
