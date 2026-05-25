from __future__ import annotations

from types import TracebackType
from typing import Protocol

from ..repository.projection_ledger_repository import (
    ProjectionLedgerRepositoryPort,
)


class ProjectionLedgerSession(Protocol):
    projection_ledger: ProjectionLedgerRepositoryPort


class ProjectionLedgerSessionScope(Protocol):
    async def __aenter__(self) -> ProjectionLedgerSession:
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        ...


class ProjectionLedgerSessionProvider(Protocol):
    def transaction(self) -> ProjectionLedgerSessionScope:
        ...
