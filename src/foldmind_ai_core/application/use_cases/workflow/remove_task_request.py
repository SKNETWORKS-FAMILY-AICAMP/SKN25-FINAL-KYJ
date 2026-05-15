from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.application.errors import ResourceNotFoundError
from foldmind_ai_core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.application.ports.outbound.workflow_runtime import WorkflowRuntimePort
from foldmind_ai_core.application.services.workflow_request_queue import (
    WorkflowRequestQueue,
)
from foldmind_ai_core.domain.workflow.tasks import TaskSnapshot

from ._task_state import mark_workflow_failed, mark_workflow_result


@dataclass(slots=True)
class RemoveTaskRequestUseCase:
    task_repository: TaskRepository
    workflow: WorkflowRuntimePort
    request_queue: WorkflowRequestQueue = field(default_factory=WorkflowRequestQueue)

    def execute(
        self,
        *,
        task_request_id: str,
    ) -> TaskSnapshot:
        snapshot = self.task_repository.get_by_request_id(
            task_request_id=task_request_id
        )
        if snapshot is None:
            raise ResourceNotFoundError(f"Task request not found: {task_request_id}")

        should_replan = self.request_queue.remove_request(snapshot, task_request_id)
        if not should_replan:
            self.task_repository.save(snapshot)
            return snapshot

        try:
            snapshot = self.workflow.run(snapshot)
            mark_workflow_result(snapshot)
        except Exception as exc:
            mark_workflow_failed(snapshot, exc)
        self.task_repository.save(snapshot)
        return snapshot
