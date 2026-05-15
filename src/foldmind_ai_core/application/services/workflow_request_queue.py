from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.domain.workflow.tasks import (
    TaskAnalysis,
    TaskAppendRequest,
    TaskCreationRequest,
    TaskRequestEntry,
    TaskRequestStatus,
    TaskSnapshot,
    TaskStatus,
)
from foldmind_ai_core.shared.validation import InvalidInputError

ACCEPTED_FOR_PLANNING_MESSAGE = "Task accepted for workflow planning."
NO_ACTIVE_REQUESTS_MESSAGE = "Task has no active requests."
REQUEST_REMOVED_REPLANNED_MESSAGE = "Task request removed. Task replanned."


@dataclass(frozen=True, slots=True)
class WorkflowRequestQueue:
    def initial_snapshot(
        self,
        request: TaskCreationRequest,
        *,
        task_id: str,
    ) -> TaskSnapshot:
        return TaskSnapshot(
            task_id=task_id,
            tenant=request.tenant,
            request=request.request,
            status=TaskStatus.CLARIFICATION_REQUIRED,
            analysis=TaskAnalysis(message=ACCEPTED_FOR_PLANNING_MESSAGE),
            requests=[self._entry_from_request(request, task_id=task_id, position=0)],
        )

    def append_request(self, snapshot: TaskSnapshot, request: TaskAppendRequest) -> None:
        snapshot.requests.append(
            self._entry_from_request(
                request,
                task_id=snapshot.task_id,
                position=len(snapshot.requests),
            )
        )
        self._prepare_for_planning(
            snapshot,
            message=ACCEPTED_FOR_PLANNING_MESSAGE,
        )

    def remove_request(self, snapshot: TaskSnapshot, task_request_id: str) -> bool:
        self._mark_removed(snapshot, task_request_id)
        self._prepare_for_planning(
            snapshot,
            message=REQUEST_REMOVED_REPLANNED_MESSAGE,
        )
        if snapshot.request:
            return True

        snapshot.analysis = TaskAnalysis(message=NO_ACTIVE_REQUESTS_MESSAGE)
        snapshot.host_actions = []
        return False

    def _prepare_for_planning(self, snapshot: TaskSnapshot, *, message: str) -> None:
        snapshot.request = self.active_request_text(snapshot.requests)
        snapshot.status = TaskStatus.CLARIFICATION_REQUIRED
        snapshot.analysis = TaskAnalysis(message=message)
        snapshot.current_action_id = None
        snapshot.error = None

    @staticmethod
    def active_request_text(requests: list[TaskRequestEntry]) -> str:
        active_requests = [
            entry.request
            for entry in sorted(requests, key=lambda item: item.position)
            if entry.status == TaskRequestStatus.ACTIVE
        ]
        return "\n\n".join(active_requests)

    @staticmethod
    def _mark_removed(snapshot: TaskSnapshot, task_request_id: str) -> None:
        for request in snapshot.requests:
            if request.task_request_id == task_request_id:
                request.status = TaskRequestStatus.REMOVED
                return
        raise InvalidInputError(f"Task request not found: {task_request_id}")

    @staticmethod
    def _entry_from_request(
        request: TaskCreationRequest | TaskAppendRequest,
        *,
        task_id: str,
        position: int,
    ) -> TaskRequestEntry:
        return TaskRequestEntry(
            task_request_id=request.task_request_id,
            task_id=task_id,
            request=request.request,
            position=position,
            status=TaskRequestStatus.ACTIVE,
        )
