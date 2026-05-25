from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.postgres.client import PostgresSessionProvider
from foldmind_ai_core.adapters.outbound.postgres.repository.task_repository import (
    TaskRepository,
)
from foldmind_ai_core.adapters.outbound.postgres.store.host_action_store import (
    HostActionStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_event_store import (
    TaskEventStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_input_store import (
    TaskInputStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_job_result_store import (
    TaskJobResultStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_job_store import (
    TaskJobStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_store import TaskStore
from foldmind_ai_core.adapters.outbound.postgres.store.tenant_storage_scope_store import (
    TenantStorageScopeStore,
)


@dataclass(slots=True)
class PostgresTaskSessionProvider:
    sessions: PostgresSessionProvider

    def close(self) -> object:
        close = getattr(self.sessions, "close", None)
        if close is None:
            return None
        return close()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[PostgresTaskSession]:
        async with self.sessions.session() as session:
            yield PostgresTaskSession(tasks=_task_repository_for_session(session))

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[PostgresTaskSession]:
        async with self.sessions.transaction() as session:
            yield PostgresTaskSession(tasks=_task_repository_for_session(session))


@dataclass(slots=True)
class PostgresTaskSession:
    tasks: TaskRepository


def _task_repository_for_session(session: object) -> TaskRepository:
    return TaskRepository(
        tenants=TenantStorageScopeStore(session),
        tasks=TaskStore(session),
        task_inputs=TaskInputStore(session),
        task_jobs=TaskJobStore(session),
        task_job_results=TaskJobResultStore(session),
        host_actions=HostActionStore(session),
        task_events=TaskEventStore(session),
    )
