from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.task import HostActionRow


class HostActionStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def task_id_for_host_action(self, action_id: str) -> str | None:
        result = await self.session.execute(
            select(HostActionRow.task_id).where(
                HostActionRow.action_id == action_id,
            )
        )
        task_id = result.scalar_one_or_none()
        if task_id is None:
            return None
        return str(task_id)

    async def action_rows_for_task(self, task_id: str) -> list[HostActionRow]:
        result = await self.session.execute(
            select(HostActionRow)
            .where(HostActionRow.task_id == task_id)
            .order_by(HostActionRow.position.asc())
        )
        return list(result.scalars().all())

    async def replace_actions_for_task(
        self,
        *,
        task_id: str,
        actions: tuple[HostActionRow, ...],
    ) -> None:
        await self.session.execute(
            delete(HostActionRow).where(HostActionRow.task_id == task_id)
        )
        if actions:
            self.session.add_all(actions)
