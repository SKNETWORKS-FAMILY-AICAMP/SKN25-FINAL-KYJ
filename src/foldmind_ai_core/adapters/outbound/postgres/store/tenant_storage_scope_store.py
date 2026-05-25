from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.sources import (
    TenantStorageScopeRow,
)


class TenantStorageScopeStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_tenant_scope(self, tenant: str) -> None:
        statement = insert(TenantStorageScopeRow).values(
            tenant_id=tenant,
            updated_at=func.now(),
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[TenantStorageScopeRow.tenant_id],
                set_={
                    "deleted_at": None,
                    "purge_after": None,
                    "updated_at": func.now(),
                },
            )
        )
