from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.commands.workflow import GetTaskQuery
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.factories.workflow_results import (
    task_result_from_snapshot,
)
from foldmind_ai_core.core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.core.application.results.workflow import TaskResult


@dataclass(slots=True)
class GetTaskUseCase:
    task_repository: TaskRepository

    def execute(self, query: GetTaskQuery) -> TaskResult:
        snapshot = self.task_repository.get(task_id=query.task_id)
        if snapshot is None:
            raise ResourceNotFoundError(f"Task not found: {query.task_id}")
        return task_result_from_snapshot(snapshot)
