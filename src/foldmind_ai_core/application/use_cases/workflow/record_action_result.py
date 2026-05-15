from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.errors import ResourceNotFoundError
from foldmind_ai_core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.application.ports.outbound.workflow_runtime import WorkflowRuntimePort
from foldmind_ai_core.domain.workflow.actions import (
    HostActionResult,
)
from foldmind_ai_core.domain.workflow.tasks import TaskSnapshot


@dataclass(slots=True)
class RecordActionResultUseCase:
    task_repository: TaskRepository
    workflow: WorkflowRuntimePort

    def execute(self, *, result: HostActionResult) -> TaskSnapshot:
        current_snapshot = self.task_repository.get_by_action_id(
            action_id=result.action_id
        )
        if current_snapshot is None:
            raise ResourceNotFoundError(f"Host action not found: {result.action_id}")

        snapshot = self.workflow.resume_from_action_result(
            task_id=current_snapshot.task_id,
            result=result,
        )
        self.task_repository.save(snapshot)
        return snapshot
