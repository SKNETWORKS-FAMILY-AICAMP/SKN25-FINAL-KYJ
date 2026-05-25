from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.postgres.client import PostgresSessionProvider
from foldmind_ai_core.adapters.outbound.postgres.repository.projection_ledger_repository import (
    ProjectionLedgerRepository,
)
from foldmind_ai_core.adapters.outbound.postgres.store.projection_ledger_store import (
    VectorProjectionRecordStore,
)


@dataclass(slots=True)
class PostgresProjectionLedgerSessionProvider:
    sessions: PostgresSessionProvider

    def close(self) -> object:
        close = getattr(self.sessions, "close", None)
        if close is None:
            return None
        return close()

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[PostgresProjectionLedgerSession]:
        async with self.sessions.transaction() as session:
            yield PostgresProjectionLedgerSession(
                projection_ledger=ProjectionLedgerRepository(
                    vector_projection_records=VectorProjectionRecordStore(session),
                )
            )


@dataclass(slots=True)
class PostgresProjectionLedgerSession:
    projection_ledger: ProjectionLedgerRepository
