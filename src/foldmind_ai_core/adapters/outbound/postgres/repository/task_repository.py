from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.adapters.outbound.postgres.mappers.task import (
    host_action_rows_from_snapshot,
    task_event_rows_from_snapshot,
    task_input_rows_from_snapshot,
    task_job_result_rows_from_snapshot,
    task_job_rows_from_snapshot,
    task_row_from_snapshot,
    task_snapshot_from_rows,
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
from foldmind_ai_core.adapters.outbound.postgres.store.task_job_store import (
    TaskJobStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_job_result_store import (
    TaskJobResultStore,
)
from foldmind_ai_core.adapters.outbound.postgres.store.task_store import TaskStore
from foldmind_ai_core.adapters.outbound.postgres.store.tenant_storage_scope_store import (
    TenantStorageScopeStore,
)
from foldmind_ai_core.core.domain.models.tasks import TaskSnapshot


@dataclass(slots=True)
class TaskRepository:
    tenants: TenantStorageScopeStore
    tasks: TaskStore
    task_inputs: TaskInputStore
    task_jobs: TaskJobStore
    task_job_results: TaskJobResultStore
    host_actions: HostActionStore
    task_events: TaskEventStore

    async def create(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        await self._save(snapshot)
        return snapshot

    async def get(self, *, task_id: str) -> TaskSnapshot | None:
        return await self._load(task_id)

    async def get_by_input_id(
        self,
        *,
        task_input_id: str,
    ) -> TaskSnapshot | None:
        task_id = await self.task_inputs.task_id_for_task_input(task_input_id)
        if task_id is None:
            return None
        return await self._load(task_id)

    async def get_by_action_id(
        self,
        *,
        action_id: str,
    ) -> TaskSnapshot | None:
        task_id = await self.host_actions.task_id_for_host_action(action_id)
        if task_id is None:
            return None
        return await self._load(task_id)

    async def save_if_unchanged(
        self,
        snapshot: TaskSnapshot,
        *,
        expected_snapshot: TaskSnapshot,
    ) -> bool:
        current_revision = await self.tasks.task_revision_for_update(snapshot.task_id)
        if current_revision is None:
            return False
        current_snapshot = await self._load(snapshot.task_id)
        if current_snapshot != expected_snapshot:
            return False
        await self._save(snapshot)
        return True

    async def _save(self, snapshot: TaskSnapshot) -> None:
        task_row = task_row_from_snapshot(snapshot)
        await self.tenants.upsert_tenant_scope(task_row.tenant)
        await self.tasks.upsert_task(task_row)
        await self.task_inputs.replace_inputs_for_task(
            task_id=snapshot.task_id,
            inputs=task_input_rows_from_snapshot(snapshot),
        )
        await self.task_jobs.replace_jobs_for_task(
            task_id=snapshot.task_id,
            jobs=task_job_rows_from_snapshot(snapshot),
        )
        await self.task_job_results.add_job_results(
            task_job_result_rows_from_snapshot(snapshot),
        )
        await self.tasks.clear_current_action(snapshot.task_id)
        await self.host_actions.replace_actions_for_task(
            task_id=snapshot.task_id,
            actions=host_action_rows_from_snapshot(snapshot),
        )
        await self.tasks.update_task_runtime(task_row)
        for event in task_event_rows_from_snapshot(snapshot):
            await self.task_events.upsert_task_event(
                task_id=snapshot.task_id,
                event=event,
            )

    async def _load(self, task_id: str) -> TaskSnapshot | None:
        row = await self.tasks.task_row_by_id(task_id)
        if row is None:
            return None
        input_rows = tuple(await self.task_inputs.input_rows_for_task(task_id))
        job_rows = tuple(await self.task_jobs.job_rows_for_task(task_id))
        job_result_rows = tuple(
            await self.task_job_results.job_result_rows_for_job_ids(
                tuple(job.job_id for job in job_rows)
            )
        )
        return task_snapshot_from_rows(
            task=row,
            inputs=input_rows,
            jobs=job_rows,
            job_results=job_result_rows,
            host_actions=tuple(await self.host_actions.action_rows_for_task(task_id)),
            events=tuple(await self.task_events.event_rows_for_task(task_id)),
        )
