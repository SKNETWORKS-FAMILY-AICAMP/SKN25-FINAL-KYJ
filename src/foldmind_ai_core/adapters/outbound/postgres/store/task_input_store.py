from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.task import TaskInputRow


class TaskInputStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def task_id_for_task_input(self, task_input_id: str) -> str | None:
        result = await self.session.execute(
            select(TaskInputRow.task_id).where(
                TaskInputRow.task_input_id == task_input_id,
            )
        )
        task_id = result.scalar_one_or_none()
        if task_id is None:
            return None
        return str(task_id)

    async def input_rows_for_task(self, task_id: str) -> list[TaskInputRow]:
        result = await self.session.execute(
            select(TaskInputRow)
            .where(TaskInputRow.task_id == task_id)
            .order_by(TaskInputRow.position.asc())
        )
        return list(result.scalars().all())

    async def replace_inputs_for_task(
        self,
        *,
        task_id: str,
        inputs: tuple[TaskInputRow, ...],
    ) -> None:
        await self.session.execute(
            delete(TaskInputRow).where(TaskInputRow.task_id == task_id)
        )
        if inputs:
            self.session.add_all(inputs)
