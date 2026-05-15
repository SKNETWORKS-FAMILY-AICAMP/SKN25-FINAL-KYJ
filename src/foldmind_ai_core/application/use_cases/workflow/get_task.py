from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.errors import ResourceNotFoundError
from foldmind_ai_core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.domain.workflow.tasks import TaskSnapshot


@dataclass(slots=True)
class GetTaskUseCase:
    task_repository: TaskRepository

    def execute(self, *, task_id: str) -> TaskSnapshot:
        snapshot = self.task_repository.get(task_id=task_id)
        if snapshot is None:
            raise ResourceNotFoundError(f"Task not found: {task_id}")
        return snapshot
