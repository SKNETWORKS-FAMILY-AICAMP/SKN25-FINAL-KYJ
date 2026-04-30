from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.models.actions import HostActionResult, HostActionResultType, HostActionStatus
from ai_core.application.models.tasks import TaskStatus
from ai_core.application.ports.task_store import TaskStore


@dataclass(slots=True)
class RecordActionResultUseCase:
    tasks: TaskStore

    def execute(self, *, tenant: str, task_id: str, result: HostActionResult) -> None:
        snapshot = self.tasks.get(tenant=tenant, task_id=task_id)
        if snapshot is None:
            raise ValueError(f"Task not found: {task_id}")

        for action in snapshot.host_actions:
            if action.action_id == result.action_id:
                action.attempts += 1
                action.status = (
                    HostActionStatus.SUCCEEDED
                    if result.outcome == HostActionResultType.SUCCEEDED
                    else HostActionStatus.FAILED
                )
                snapshot.current_action_id = action.action_id
                break

        if snapshot.host_actions and all(
            action.status == HostActionStatus.SUCCEEDED for action in snapshot.host_actions
        ):
            snapshot.status = TaskStatus.COMPLETED
        elif result.outcome == HostActionResultType.FAILED:
            snapshot.status = TaskStatus.FAILED

        self.tasks.save(snapshot)
