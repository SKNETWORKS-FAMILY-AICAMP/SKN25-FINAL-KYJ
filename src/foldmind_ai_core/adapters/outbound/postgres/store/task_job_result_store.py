from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.task import TaskJobResultRow


class TaskJobResultStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def job_result_rows_for_job_ids(
        self,
        job_ids: tuple[str, ...],
    ) -> list[TaskJobResultRow]:
        if not job_ids:
            return []
        result = await self.session.execute(
            select(TaskJobResultRow)
            .where(TaskJobResultRow.job_id.in_(job_ids))
            .order_by(TaskJobResultRow.job_id.asc(), TaskJobResultRow.position.asc())
        )
        return list(result.scalars().all())

    async def add_job_results(
        self,
        job_results: tuple[TaskJobResultRow, ...],
    ) -> None:
        if job_results:
            self.session.add_all(job_results)
