from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.task import TaskEventRow


class TaskEventStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def event_rows_for_task(self, task_id: str) -> list[TaskEventRow]:
        result = await self.session.execute(
            select(TaskEventRow)
            .where(TaskEventRow.task_id == task_id)
            .order_by(TaskEventRow.created_at.asc(), TaskEventRow.event_id.asc())
        )
        return list(result.scalars().all())

    async def upsert_task_event(self, *, task_id: str, event: TaskEventRow) -> None:
        await self.session.execute(_upsert_task_event(task_id=task_id, event=event))


def _upsert_task_event(*, task_id: str, event: TaskEventRow) -> Insert:
    statement = insert(TaskEventRow).values(
        task_id=task_id,
        job_id=event.job_id,
        event_id=event.event_id,
        event_type=event.event_type,
        message=event.message,
        data_json=event.data_json,
    )
    excluded = statement.excluded
    return statement.on_conflict_do_update(
        index_elements=[TaskEventRow.event_id],
        set_={
            "job_id": excluded.job_id,
            "event_type": excluded.event_type,
            "message": excluded.message,
            "data_json": excluded.data_json,
        },
    )
