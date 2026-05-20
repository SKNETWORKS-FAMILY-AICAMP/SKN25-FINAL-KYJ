from __future__ import annotations

import unittest

from foldmind_ai_core.core.domain.services.workflow_inputs import (
    WorkflowInputQueue,
)
from foldmind_ai_core.core.domain.services.workflow import (
    mark_workflow_failed,
    mark_workflow_result,
)
from foldmind_ai_core.core.domain.models.workflow.actions import (
    HostAction,
    HostActionStatus,
    HostActionType,
    MoveDocumentInput,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAppendInput,
    TaskContext,
    TaskCreationInput,
    TaskInputStatus,
    TaskSnapshot,
    TaskStatus,
)

REQUESTED_AT = "2026-05-17T09:30:00+09:00"


class WorkflowInputQueueTests(unittest.TestCase):
    def test_request_queue_owns_request_state_transitions(self) -> None:
        queue = WorkflowInputQueue()
        snapshot = queue.initial_snapshot(
            TaskCreationInput(
                tenant="tenant-1",
                request="First request",
                context=TaskContext(
                    requested_at=REQUESTED_AT,
                    document_id="doc-1",
                    folder_id="folder-1",
                ),
                task_input_id="request-1",
            ),
            task_id="task-1",
        )
        snapshot.status = TaskStatus.READY_FOR_HOST_ACTION
        snapshot.current_action_id = "action-1"
        snapshot.error = "stale error"
        snapshot.metadata["workflow_feedback"] = "stale feedback"
        snapshot.metadata["document"] = {"document_id": "doc-1"}
        snapshot.host_actions = [
            HostAction(
                action_type=HostActionType.MOVE_DOCUMENT,
                summary="Move document.",
                input=MoveDocumentInput(
                    document_type="document",
                    document_id="doc-1",
                    target_folder_id="folder-1",
                ),
            )
        ]

        queue.append_input(
            snapshot,
            TaskAppendInput(
                request="Second request",
                context=TaskContext(requested_at="2026-05-17T10:00:00+09:00"),
                task_id="task-1",
                task_input_id="request-2",
            ),
        )
        should_replan = queue.remove_input(snapshot, "request-1")

        self.assertTrue(should_replan)
        self.assertEqual(snapshot.request, "Second request")
        self.assertEqual(snapshot.status, TaskStatus.CLARIFICATION_REQUIRED)
        self.assertIsNone(snapshot.current_action_id)
        self.assertIsNone(snapshot.error)
        self.assertEqual(snapshot.host_actions, [])
        self.assertEqual(snapshot.metadata, {"document": {"document_id": "doc-1"}})
        self.assertEqual(snapshot.context.requested_at, "2026-05-17T10:00:00+09:00")
        self.assertEqual(snapshot.context.document_id, "doc-1")
        self.assertEqual(snapshot.context.folder_id, "folder-1")
        self.assertEqual(snapshot.inputs[0].status, TaskInputStatus.REMOVED)
        self.assertEqual(snapshot.analysis.message, "Task input removed. Task replanned.")

        snapshot.host_actions = [
            HostAction(
                action_type=HostActionType.MOVE_DOCUMENT,
                summary="Move document.",
                input=MoveDocumentInput(
                    document_type="document",
                    document_id="doc-1",
                    target_folder_id="folder-1",
                ),
            )
        ]
        should_replan = queue.remove_input(snapshot, "request-2")

        self.assertFalse(should_replan)
        self.assertEqual(snapshot.request, "")
        self.assertEqual(snapshot.host_actions, [])
        self.assertEqual(snapshot.analysis.message, "Task has no active inputs.")

    def test_removing_already_removed_request_does_not_replan(self) -> None:
        queue = WorkflowInputQueue()
        snapshot = queue.initial_snapshot(
            TaskCreationInput(
                tenant="tenant-1",
                request="First request",
                context=TaskContext(requested_at=REQUESTED_AT),
                task_input_id="request-1",
            ),
            task_id="task-1",
        )
        queue.append_input(
            snapshot,
            TaskAppendInput(
                request="Second request",
                context=TaskContext(requested_at="2026-05-17T10:00:00+09:00"),
                task_id="task-1",
                task_input_id="request-2",
            ),
        )
        queue.remove_input(snapshot, "request-1")
        snapshot.status = TaskStatus.READY_FOR_HOST_ACTION
        snapshot.current_action_id = "action-1"
        snapshot.analysis.message = "Task is ready for host action."

        should_replan = queue.remove_input(snapshot, "request-1")

        self.assertFalse(should_replan)
        self.assertEqual(snapshot.request, "Second request")
        self.assertEqual(snapshot.status, TaskStatus.READY_FOR_HOST_ACTION)
        self.assertEqual(snapshot.current_action_id, "action-1")
        self.assertEqual(snapshot.analysis.message, "Task is ready for host action.")

    def test_workflow_result_marker_uses_host_action_state(self) -> None:
        queue = WorkflowInputQueue()
        snapshot = queue.initial_snapshot(
            TaskCreationInput(
                tenant="tenant-1",
                request="Create a plan",
                context=TaskContext(requested_at=REQUESTED_AT),
                task_input_id="request-1",
            ),
            task_id="task-1",
        )
        action = HostAction(
            action_type=HostActionType.MOVE_DOCUMENT,
            summary="Move document.",
            input=MoveDocumentInput(
                document_type="document",
                document_id="doc-1",
                target_folder_id="folder-1",
            ),
            status=HostActionStatus.READY,
        )
        snapshot.host_actions.append(action)

        mark_workflow_result(snapshot)

        self.assertEqual(snapshot.status, TaskStatus.READY_FOR_HOST_ACTION)
        self.assertEqual(snapshot.current_action_id, action.action_id)

    def test_workflow_result_marker_stops_on_failed_host_action(self) -> None:
        queue = WorkflowInputQueue()
        snapshot = queue.initial_snapshot(
            TaskCreationInput(
                tenant="tenant-1",
                request="Create a plan",
                context=TaskContext(requested_at=REQUESTED_AT),
                task_input_id="request-1",
            ),
            task_id="task-1",
        )
        failed_action = HostAction(
            action_type=HostActionType.MOVE_DOCUMENT,
            summary="Move document.",
            input=MoveDocumentInput(
                document_type="document",
                document_id="doc-1",
                target_folder_id="folder-1",
            ),
            status=HostActionStatus.FAILED,
        )
        later_action = HostAction(
            action_type=HostActionType.MOVE_DOCUMENT,
            summary="Move another document.",
            input=MoveDocumentInput(
                document_type="document",
                document_id="doc-2",
                target_folder_id="folder-1",
            ),
            status=HostActionStatus.READY,
        )
        snapshot.host_actions.extend([failed_action, later_action])

        mark_workflow_result(snapshot)

        self.assertEqual(snapshot.status, TaskStatus.FAILED)
        self.assertIsNone(snapshot.current_action_id)
        self.assertEqual(snapshot.error, "Host action failed.")
        self.assertEqual(snapshot.analysis.message, "Task failed.")

    def test_workflow_failure_marker_fails_incomplete_actions(self) -> None:
        queue = WorkflowInputQueue()
        snapshot = queue.initial_snapshot(
            TaskCreationInput(
                tenant="tenant-1",
                request="Create a plan",
                context=TaskContext(requested_at=REQUESTED_AT),
                task_input_id="request-1",
            ),
            task_id="task-1",
        )
        action = HostAction(
            action_type=HostActionType.MOVE_DOCUMENT,
            summary="Move document.",
            input=MoveDocumentInput(
                document_type="document",
                document_id="doc-1",
                target_folder_id="folder-1",
            ),
            status=HostActionStatus.PROPOSED,
        )
        snapshot.host_actions.append(action)

        mark_workflow_failed(snapshot, RuntimeError("boom"))

        self.assertEqual(snapshot.status, TaskStatus.FAILED)
        self.assertEqual(action.status, HostActionStatus.FAILED)
        self.assertEqual(snapshot.error, "boom")


if __name__ == "__main__":
    unittest.main()
