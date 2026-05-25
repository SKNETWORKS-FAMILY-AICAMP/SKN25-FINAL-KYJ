from __future__ import annotations

import unittest

from foldmind_ai_core.core.application.workflows.host_actions.result_service import (
    HostActionResultService,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.domain.models.host_actions import (
    CreateDocumentInput,
    CreateFolderInput,
    HostAction,
    HostActionPolicy,
    HostActionResult,
    HostActionResultType,
    HostActionStatus,
    HostActionType,
    LinkDocumentsInput,
)
from foldmind_ai_core.core.domain.models.tasks import (
    TaskAnalysis,
    TaskContext,
    TaskSnapshot,
    TaskStatus,
)

ACTION_ID = "action-1"
TASK_ID = "55555555-5555-4555-8555-555555555555"


class HostActionResultServiceTests(unittest.TestCase):
    def test_merge_schedules_first_ready_action_by_position(self) -> None:
        action = _host_action(
            policy=HostActionPolicy(requires_confirmation=False),
        )
        action.status = HostActionStatus.READY
        later_action = _host_action(
            action_id="action-2",
            policy=HostActionPolicy(requires_confirmation=False),
        )
        later_action.status = HostActionStatus.READY
        state = _state()
        service = HostActionResultService()

        service.merge_host_actions(state, [action, later_action])

        self.assertEqual(state.task.host_actions, [action, later_action])
        self.assertEqual(state.pending_actions, [action])

    def test_approved_action_is_scheduled_without_retry_message(self) -> None:
        action = _host_action()
        state = _state(action)
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.APPROVED,
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(action.status, HostActionStatus.READY)
        self.assertEqual(state.retry_action_id, ACTION_ID)
        self.assertEqual(state.task.status, TaskStatus.READY_FOR_HOST_ACTION)
        self.assertEqual(state.task.analysis.message, "Task is ready for host action.")

        service.retry_host_action(state)

        self.assertEqual(state.retry_action_id, None)
        self.assertEqual(state.pending_actions, [action])
        self.assertEqual(state.task.analysis.message, "Task is ready for host action.")

    def test_retryable_failed_action_uses_retry_message(self) -> None:
        action = _host_action(
            policy=HostActionPolicy(retryable=True, max_attempts=2),
        )
        state = _state(action)
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.FAILED,
            error="Temporary failure.",
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(action.status, HostActionStatus.READY)
        self.assertEqual(action.attempts, 1)
        self.assertEqual(state.retry_action_id, ACTION_ID)
        self.assertEqual(state.task.status, TaskStatus.READY_FOR_HOST_ACTION)
        self.assertEqual(state.task.analysis.message, "Host action retry requested.")

        service.retry_host_action(state)

        self.assertEqual(state.retry_action_id, None)
        self.assertEqual(state.pending_actions, [action])
        self.assertEqual(state.task.analysis.message, "Host action retry scheduled.")

    def test_allowed_skipped_action_completes_task(self) -> None:
        action = _host_action(policy=HostActionPolicy(allow_skip=True))
        state = _state(action)
        state.pending_actions = [action]
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.SKIPPED,
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(action.status, HostActionStatus.SKIPPED)
        self.assertEqual(state.pending_actions, [])
        self.assertIsNone(state.task.current_action_id)
        self.assertEqual(state.task.status, TaskStatus.COMPLETED)
        self.assertEqual(state.task.analysis.message, "Task completed.")

    def test_skipped_action_does_not_skip_later_action(self) -> None:
        action = _host_action(policy=HostActionPolicy(allow_skip=True))
        later_action = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create child folder.",
            input=CreateFolderInput(name="Child"),
            action_id="action-2",
        )
        state = _state(action)
        state.task.host_actions.append(later_action)
        state.pending_actions = [action]
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.SKIPPED,
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(action.status, HostActionStatus.SKIPPED)
        self.assertEqual(later_action.status, HostActionStatus.PROPOSED)
        self.assertEqual(state.pending_actions, [later_action])
        self.assertEqual(state.task.current_action_id, later_action.action_id)
        self.assertEqual(state.task.status, TaskStatus.AWAITING_DECISION)

    def test_disallowed_skipped_action_fails_task(self) -> None:
        action = _host_action()
        state = _state(action)
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.SKIPPED,
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(action.status, HostActionStatus.FAILED)
        self.assertIsNone(state.task.current_action_id)
        self.assertEqual(state.task.status, TaskStatus.FAILED)
        self.assertEqual(state.task.error, "Host action failed.")

    def test_successful_action_waits_for_confirmation_before_next_action(
        self,
    ) -> None:
        action = _host_action(
            policy=HostActionPolicy(requires_confirmation=False),
        )
        action.status = HostActionStatus.READY
        later_action = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create child folder.",
            input=CreateFolderInput(name="Child"),
            action_id="action-2",
        )
        state = _state(action)
        state.task.host_actions.append(later_action)
        state.pending_actions = [action]
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.SUCCEEDED,
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(action.status, HostActionStatus.SUCCEEDED)
        self.assertEqual(later_action.status, HostActionStatus.PROPOSED)
        self.assertEqual(state.pending_actions, [later_action])
        self.assertEqual(state.task.status, TaskStatus.AWAITING_DECISION)
        self.assertEqual(state.task.current_action_id, later_action.action_id)

    def test_successful_folder_action_requires_output_for_dependent_document(
        self,
    ) -> None:
        action = _host_action(
            policy=HostActionPolicy(requires_confirmation=False),
        )
        action.status = HostActionStatus.READY
        later_action = HostAction(
            action_type=HostActionType.CREATE_DOCUMENT,
            summary="Create document.",
            input=CreateDocumentInput(
                title="Report",
                body="Body",
                metadata={"folder_action_id": ACTION_ID},
            ),
            action_id="action-2",
        )
        state = _state(action)
        state.task.host_actions.append(later_action)
        state.pending_actions = [action]
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.SUCCEEDED,
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(action.status, HostActionStatus.FAILED)
        self.assertEqual(state.pending_actions, [])
        self.assertEqual(state.task.status, TaskStatus.FAILED)
        self.assertEqual(
            state.task.error,
            "Create folder output is required for dependent document actions.",
        )

    def test_successful_document_action_requires_output_for_dependent_link(
        self,
    ) -> None:
        action = HostAction(
            action_type=HostActionType.CREATE_DOCUMENT,
            summary="Create document.",
            input=CreateDocumentInput(title="Report", body="Body"),
            action_id=ACTION_ID,
            status=HostActionStatus.READY,
            policy=HostActionPolicy(requires_confirmation=False),
        )
        later_action = HostAction(
            action_type=HostActionType.LINK_DOCUMENTS,
            summary="Link document.",
            input=LinkDocumentsInput(
                source_type="document",
                source_id=ACTION_ID,
                target_type="document",
                target_id="target-doc",
            ),
            action_id="action-2",
        )
        state = _state(action)
        state.task.host_actions.append(later_action)
        state.pending_actions = [action]
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.SUCCEEDED,
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(action.status, HostActionStatus.FAILED)
        self.assertEqual(state.pending_actions, [])
        self.assertEqual(state.task.status, TaskStatus.FAILED)
        self.assertEqual(
            state.task.error,
            "Create document output is required for dependent link actions.",
        )

    def test_successful_action_schedules_unconfirmed_next_action(self) -> None:
        action = _host_action(
            policy=HostActionPolicy(requires_confirmation=False),
        )
        action.status = HostActionStatus.READY
        later_action = HostAction(
            action_type=HostActionType.CREATE_FOLDER,
            summary="Create child folder.",
            input=CreateFolderInput(name="Child"),
            action_id="action-2",
            policy=HostActionPolicy(requires_confirmation=False),
        )
        state = _state(action)
        state.task.host_actions.append(later_action)
        state.pending_actions = [action]
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.SUCCEEDED,
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(later_action.status, HostActionStatus.READY)
        self.assertEqual(state.pending_actions, [later_action])
        self.assertEqual(state.task.status, TaskStatus.READY_FOR_HOST_ACTION)

    def test_rejected_action_clears_other_pending_actions(self) -> None:
        action = _host_action()
        other_action = _host_action(action_id="action-2")
        other_action.status = HostActionStatus.READY
        state = _state(action)
        state.task.host_actions.append(other_action)
        state.pending_actions = [action, other_action]
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.REJECTED,
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(state.pending_actions, [])
        self.assertIsNone(state.task.current_action_id)
        self.assertEqual(state.task.status, TaskStatus.REJECTED)
        self.assertEqual(state.task.analysis.message, "Task rejected.")

    def test_modified_action_clears_pending_actions_before_replan(self) -> None:
        action = _host_action()
        other_action = _host_action(action_id="action-2")
        other_action.status = HostActionStatus.READY
        state = _state(action)
        state.task.host_actions.append(other_action)
        state.pending_actions = [action, other_action]
        state.task.current_action_id = ACTION_ID
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.MODIFIED,
            metadata={"modified_request": "Create a revised folder."},
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertTrue(state.needs_replan)
        self.assertEqual(state.pending_actions, [])
        self.assertIsNone(state.task.current_action_id)
        self.assertEqual(state.task.status, TaskStatus.CLARIFICATION_REQUIRED)
        self.assertEqual(state.task.request, "Create a revised folder.")

    def test_final_failed_action_clears_other_pending_actions(self) -> None:
        action = _host_action(policy=HostActionPolicy(retryable=False, max_attempts=1))
        action.status = HostActionStatus.READY
        other_action = _host_action(action_id="action-2")
        other_action.status = HostActionStatus.READY
        state = _state(action)
        state.task.host_actions.append(other_action)
        state.pending_actions = [action, other_action]
        result = HostActionResult(
            action_id=ACTION_ID,
            outcome=HostActionResultType.FAILED,
            error="Permanent failure.",
        )
        service = HostActionResultService()

        service.apply(state, result)

        self.assertEqual(action.status, HostActionStatus.FAILED)
        self.assertEqual(state.pending_actions, [])
        self.assertIsNone(state.task.current_action_id)
        self.assertEqual(state.task.status, TaskStatus.FAILED)
        self.assertEqual(state.task.error, "Permanent failure.")


def _host_action(
    *,
    action_id: str = ACTION_ID,
    policy: HostActionPolicy | None = None,
) -> HostAction:
    return HostAction(
        action_type=HostActionType.CREATE_FOLDER,
        summary="Create a folder.",
        input=CreateFolderInput(name="Projects"),
        action_id=action_id,
        policy=policy or HostActionPolicy(),
    )


def _state(action: HostAction | None = None) -> WorkflowState:
    return WorkflowState(
        task=TaskSnapshot(
            task_id=TASK_ID,
            tenant="tenant-1",
            request="Create a folder.",
            context=TaskContext(requested_at="2026-05-17T09:30:00+09:00"),
            status=TaskStatus.AWAITING_DECISION,
            analysis=TaskAnalysis(message="Waiting for approval."),
            host_actions=[action] if action is not None else [],
        )
    )


if __name__ == "__main__":
    unittest.main()
