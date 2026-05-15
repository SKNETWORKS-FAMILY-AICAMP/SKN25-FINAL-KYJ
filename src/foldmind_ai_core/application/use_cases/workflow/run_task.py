from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.application.ports.outbound.workflow_runtime import WorkflowRuntimePort
from foldmind_ai_core.application.services.workflow_request_queue import (
    WorkflowRequestQueue,
)
from foldmind_ai_core.domain.workflow.tasks import (
    TaskAppendRequest,
    TaskCreationRequest,
    TaskSnapshot,
)
from foldmind_ai_core.shared.internal_ids import new_internal_id
from foldmind_ai_core.shared.validation import InvalidInputError

from ._task_state import mark_workflow_failed, mark_workflow_result


@dataclass(slots=True)
class RunTaskUseCase:
    task_repository: TaskRepository
    workflow: WorkflowRuntimePort
    request_queue: WorkflowRequestQueue = field(default_factory=WorkflowRequestQueue)

    def execute(self, request: TaskCreationRequest | TaskAppendRequest) -> TaskSnapshot:
        snapshot = self._snapshot_for_request(request)

        try:
            snapshot = self.workflow.run(snapshot)
            mark_workflow_result(snapshot)
        except Exception as exc:
            mark_workflow_failed(snapshot, exc)

        self.task_repository.save(snapshot)
        return snapshot

    def _snapshot_for_request(
        self,
        request: TaskCreationRequest | TaskAppendRequest,
    ) -> TaskSnapshot:
        if isinstance(request, TaskCreationRequest):
            snapshot = self.request_queue.initial_snapshot(
                request,
                task_id=new_internal_id(),
            )
            self.task_repository.create(snapshot)
            return snapshot

        snapshot = self.task_repository.get(task_id=request.task_id)
        if snapshot is None:
            raise InvalidInputError(f"Task not found: {request.task_id}")
        self.request_queue.append_request(snapshot, request)
        return snapshot
