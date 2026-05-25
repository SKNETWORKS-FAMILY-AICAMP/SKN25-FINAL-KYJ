from __future__ import annotations

from types import TracebackType
from typing import Protocol

from foldmind_ai_core.core.application.ports.outbound.repository.task_repository import (
    TaskRepositoryPort,
)


class TaskSession(Protocol):
    tasks: TaskRepositoryPort


class TaskSessionScope(Protocol):
    async def __aenter__(self) -> TaskSession:
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        ...


class TaskSessionProvider(Protocol):
    def session(self) -> TaskSessionScope:
        ...

    def transaction(self) -> TaskSessionScope:
        ...
