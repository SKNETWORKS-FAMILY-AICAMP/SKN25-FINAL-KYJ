from __future__ import annotations

from sqlalchemy import Text, func, literal_column, select, update
from sqlalchemy.dialects.postgresql import Insert, insert
from sqlalchemy.ext.asyncio import AsyncSession

from foldmind_ai_core.adapters.outbound.postgres.models.task import TaskRow


class TaskStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def task_row_by_id(self, task_id: str) -> TaskRow | None:
        result = await self.session.execute(
            select(TaskRow).where(TaskRow.task_id == task_id)
        )
        return result.scalar_one_or_none()

    async def task_revision(self, task_id: str) -> str | None:
        result = await self.session.execute(
            select(literal_column("xmin", type_=Text()))
            .select_from(TaskRow)
            .where(TaskRow.task_id == task_id)
        )
        revision = result.scalar_one_or_none()
        if revision is None:
            return None
        return str(revision)

    async def task_revision_for_update(self, task_id: str) -> str | None:
        result = await self.session.execute(
            select(literal_column("xmin", type_=Text()))
            .select_from(TaskRow)
            .where(TaskRow.task_id == task_id)
            .with_for_update()
        )
        revision = result.scalar_one_or_none()
        if revision is None:
            return None
        return str(revision)

    async def upsert_task(self, task: TaskRow) -> None:
        await self.session.execute(_upsert_task_statement(task))

    async def update_task_runtime(self, task: TaskRow) -> None:
        await self.session.execute(
            update(TaskRow)
            .where(TaskRow.task_id == task.task_id)
            .values(
                current_action_id=task.current_action_id,
                error_json=task.error_json,
                updated_at=func.now(),
            )
        )

    async def clear_current_action(self, task_id: str) -> None:
        await self.session.execute(
            update(TaskRow)
            .where(TaskRow.task_id == task_id)
            .values(current_action_id=None)
        )


def _upsert_task_statement(task: TaskRow) -> Insert:
    statement = insert(TaskRow).values(
        tenant=task.tenant,
        task_id=task.task_id,
        request_text=task.request_text,
        context_json=task.context_json,
        status=task.status,
        analysis_message=task.analysis_message,
        result_type=task.result_type,
        result_json=task.result_json,
        result_title=task.result_title,
        result_metadata=task.result_metadata,
        completed_at=task.completed_at,
        metadata_json=task.metadata_json,
        updated_at=func.now(),
    )
    excluded = statement.excluded
    return statement.on_conflict_do_update(
        index_elements=[TaskRow.task_id],
        set_={
            "tenant": excluded.tenant,
            "request_text": excluded.request_text,
            "context_json": excluded.context_json,
            "status": excluded.status,
            "analysis_message": excluded.analysis_message,
            "result_type": excluded.result_type,
            "result_json": excluded.result_json,
            "result_title": excluded.result_title,
            "result_metadata": excluded.result_metadata,
            "metadata_json": excluded.metadata_json,
            "completed_at": func.coalesce(TaskRow.completed_at, excluded.completed_at),
            "updated_at": func.now(),
        },
    )
