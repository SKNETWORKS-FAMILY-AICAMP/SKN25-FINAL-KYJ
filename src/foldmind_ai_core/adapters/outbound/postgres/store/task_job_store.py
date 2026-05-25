from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.task import (
    TaskJobRow,
)


class TaskJobStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def job_rows_for_task(self, task_id: str) -> list[TaskJobRow]:
        result = await self.session.execute(
            select(TaskJobRow)
            .where(TaskJobRow.task_id == task_id)
            .order_by(TaskJobRow.round_index.asc(), TaskJobRow.position.asc())
        )
        return list(result.scalars().all())

    async def replace_jobs_for_task(
        self,
        *,
        task_id: str,
        jobs: tuple[TaskJobRow, ...],
    ) -> None:
        await self.session.execute(
            delete(TaskJobRow).where(TaskJobRow.task_id == task_id)
        )
        if jobs:
            self.session.add_all(jobs)
            await self.session.flush()
