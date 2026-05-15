from __future__ import annotations

from foldmind_ai_core.domain.workflow.actions import HostActionStatus
from foldmind_ai_core.domain.workflow.tasks import (
    TaskAnalysis,
    TaskSnapshot,
    TaskStatus,
)


def mark_workflow_result(snapshot: TaskSnapshot) -> None:
    ready_actions = [
        action
        for action in snapshot.host_actions
        if action.status == HostActionStatus.READY
    ]
    if ready_actions:
        snapshot.status = TaskStatus.READY_FOR_HOST_ACTION
        snapshot.current_action_id = ready_actions[0].action_id
        snapshot.analysis.message = "Task is ready for host action."
        return

    if snapshot.host_actions:
        snapshot.status = TaskStatus.AWAITING_DECISION
        snapshot.analysis.message = "Task is awaiting a host action decision."
        return

    snapshot.status = TaskStatus.COMPLETED
    snapshot.analysis.message = "Task completed."


def mark_workflow_failed(snapshot: TaskSnapshot, exc: Exception) -> None:
    snapshot.status = TaskStatus.FAILED
    snapshot.error = str(exc)
    snapshot.analysis = TaskAnalysis(message="Task failed.")
