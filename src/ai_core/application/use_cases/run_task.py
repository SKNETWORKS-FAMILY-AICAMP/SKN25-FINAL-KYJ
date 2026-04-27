from __future__ import annotations

from dataclasses import dataclass

from ai_core.application.ports.task_store import TaskStore
from ai_core.domain.tasks import TaskAnalysis, TaskRequest, TaskSnapshot, TaskStatus


@dataclass(slots=True)
class RunTaskUseCase:
    tasks: TaskStore

    def execute(self, request: TaskRequest) -> TaskSnapshot:
        snapshot = TaskSnapshot(
            task_id=request.task_id,
            tenant=request.tenant,
            request=request.request,
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(response="Task accepted for workflow planning."),
            user_id=request.user_id,
            request_id=request.request_id,
            metadata=dict(request.context),
        )
        self.tasks.create(request, snapshot)
        return snapshot
