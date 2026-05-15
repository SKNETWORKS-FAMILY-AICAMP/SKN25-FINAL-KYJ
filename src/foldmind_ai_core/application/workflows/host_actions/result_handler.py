from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.domain.workflow.actions import (
    CreateDocumentInput,
    CreateDocumentOutput,
    CreateFolderOutput,
    HostAction,
    HostActionResult,
    HostActionResultType,
    HostActionStatus,
    LinkDocumentsInput,
)
from foldmind_ai_core.domain.workflow.tasks import TaskStatus

_ATTEMPT_OUTCOMES = {
    HostActionResultType.SUCCEEDED,
    HostActionResultType.FAILED,
    HostActionResultType.RETRY,
}
_SKIPPED_OUTCOMES = {
    HostActionResultType.REJECTED,
    HostActionResultType.MODIFIED,
    HostActionResultType.SKIPPED,
}


@dataclass(slots=True)
class HostActionResultHandler:
    def apply(self, state: WorkflowState, result: HostActionResult) -> WorkflowState:
        state.last_action_result = result
        state.needs_replan = False
        state.retry_action_id = None
        state.last_error = None
        self._apply_action_feedback(state, result)
        action = self._find_action(state, result.action_id)
        if action is not None:
            if result.outcome in _ATTEMPT_OUTCOMES:
                action.attempts += 1
            action.status = self._action_status_for_result(action, result)
            state.task.current_action_id = action.action_id
            state.needs_replan = result.outcome == HostActionResultType.MODIFIED
            if self._should_schedule_action(action, result):
                state.retry_action_id = action.action_id
            if result.outcome == HostActionResultType.SUCCEEDED:
                self._apply_successful_action_output(state, action, result)

        state.pending_actions = [
            action
            for action in state.pending_actions
            if action.action_id != result.action_id
        ]
        self.schedule_unblocked_actions(state)
        if state.pending_actions:
            state.task.current_action_id = state.pending_actions[0].action_id

        self._apply_task_status(state, result)
        return state

    def _apply_task_status(self, state: WorkflowState, result: HostActionResult) -> None:
        if state.needs_replan:
            state.task.status = TaskStatus.CLARIFICATION_REQUIRED
            state.task.analysis.message = "Task needs replanning."
            return

        has_pending_host_work = state.retry_action_id is not None or bool(state.pending_actions)
        if has_pending_host_work:
            state.task.status = TaskStatus.READY_FOR_HOST_ACTION
            state.task.analysis.message = (
                "Host action retry requested."
                if state.retry_action_id is not None
                else "Task is ready for host action."
            )
            return
        if result.outcome == HostActionResultType.REJECTED:
            state.task.status = TaskStatus.REJECTED
            state.task.analysis.message = "Task rejected."
            return

        if self._all_host_actions_succeeded(state):
            state.task.status = TaskStatus.COMPLETED
            state.task.analysis.message = "Task completed."
            return
        if result.outcome == HostActionResultType.FAILED:
            state.task.status = TaskStatus.FAILED
            state.task.error = result.error
            state.task.analysis.message = "Task failed."

    def _find_action(self, state: WorkflowState, action_id: str) -> HostAction | None:
        return next(
            (action for action in state.task.host_actions if action.action_id == action_id),
            None,
        )

    def retry_host_action(self, state: WorkflowState) -> WorkflowState:
        retry_action_id = state.retry_action_id
        state.retry_action_id = None
        if retry_action_id is None:
            return state

        for action in state.task.host_actions:
            if action.action_id != retry_action_id:
                continue
            action.status = HostActionStatus.READY
            if action not in state.pending_actions:
                state.pending_actions.append(action)
            state.task.current_action_id = retry_action_id
            state.task.status = TaskStatus.READY_FOR_HOST_ACTION
            state.task.analysis.message = "Host action retry scheduled."
            break
        return state

    def merge_host_actions(self, state: WorkflowState, actions: list[HostAction]) -> None:
        existing_action_ids = {
            action.action_id
            for action in state.task.host_actions
            if action.action_id is not None
        }
        for action in actions:
            action_id = action.action_id
            if action_id is not None and action_id in existing_action_ids:
                continue
            state.task.host_actions.append(action)

            is_unblocked_proposal = (
                action.status == HostActionStatus.PROPOSED
                and self.dependencies_satisfied(action, state.task.host_actions)
            )
            if is_unblocked_proposal:
                action.status = HostActionStatus.READY
            if action.status == HostActionStatus.READY:
                state.pending_actions.append(action)
            if action_id is not None:
                existing_action_ids.add(action_id)

    def schedule_unblocked_actions(self, state: WorkflowState) -> None:
        pending_action_ids = {
            action.action_id
            for action in state.pending_actions
            if action.action_id is not None
        }
        for action in state.task.host_actions:
            action_id = action.action_id
            if action_id is None or action_id in pending_action_ids:
                continue
            if not self.dependencies_satisfied(action, state.task.host_actions):
                continue
            if action.status == HostActionStatus.PROPOSED:
                action.status = HostActionStatus.READY
            if action.status != HostActionStatus.READY:
                continue
            state.pending_actions.append(action)
            pending_action_ids.add(action_id)

    def dependencies_satisfied(
        self,
        action: HostAction,
        actions: list[HostAction],
    ) -> bool:
        if not action.depends_on:
            return True
        statuses = {
            candidate.action_id: candidate.status
            for candidate in actions
            if candidate.action_id is not None
        }
        return all(
            statuses.get(action_id) == HostActionStatus.SUCCEEDED
            for action_id in action.depends_on
        )

    def _apply_successful_action_output(
        self,
        state: WorkflowState,
        action: HostAction,
        result: HostActionResult,
    ) -> None:
        if isinstance(result.output, CreateDocumentOutput):
            self._apply_created_document_output(state, action, result.output)
            return
        if isinstance(result.output, CreateFolderOutput):
            self._apply_created_folder_output(state, action, result.output)

    def _apply_created_folder_output(
        self,
        state: WorkflowState,
        action: HostAction,
        output: CreateFolderOutput,
    ) -> None:
        for candidate in state.task.host_actions:
            if action.action_id not in candidate.depends_on:
                continue
            if not isinstance(candidate.input, CreateDocumentInput):
                continue
            if candidate.input.folder_id is None:
                candidate.input.folder_id = output.folder_id

    def _apply_created_document_output(
        self,
        state: WorkflowState,
        action: HostAction,
        output: CreateDocumentOutput,
    ) -> None:
        for candidate in state.task.host_actions:
            if action.action_id not in candidate.depends_on:
                continue
            if not isinstance(candidate.input, LinkDocumentsInput):
                continue
            if candidate.input.source_id != action.action_id:
                continue
            candidate.input.source_type = output.created_document_type
            candidate.input.source_id = output.created_document_id
            if output.source_version is not None:
                candidate.input.metadata["source_version"] = output.source_version

    def _action_status_for_result(
        self,
        action: HostAction,
        result: HostActionResult,
    ) -> HostActionStatus:
        if result.outcome == HostActionResultType.SUCCEEDED:
            return HostActionStatus.SUCCEEDED
        if result.outcome == HostActionResultType.APPROVED:
            return HostActionStatus.READY
        if result.outcome in _SKIPPED_OUTCOMES:
            return HostActionStatus.SKIPPED

        can_retry_after_failure = (
            result.outcome in {HostActionResultType.FAILED, HostActionResultType.RETRY}
            and self._can_retry_action(action, result)
        )
        if can_retry_after_failure:
            return HostActionStatus.READY
        return HostActionStatus.FAILED

    def _should_schedule_action(
        self,
        action: HostAction,
        result: HostActionResult,
    ) -> bool:
        if result.outcome == HostActionResultType.APPROVED:
            return True
        if result.outcome not in {HostActionResultType.FAILED, HostActionResultType.RETRY}:
            return False
        return self._can_retry_action(action, result)

    def _all_host_actions_succeeded(self, state: WorkflowState) -> bool:
        return bool(state.task.host_actions) and all(
            action.status == HostActionStatus.SUCCEEDED
            for action in state.task.host_actions
        )

    def _can_retry_action(
        self,
        action: HostAction,
        result: HostActionResult,
    ) -> bool:
        if result.outcome == HostActionResultType.RETRY:
            return action.attempts < action.policy.max_attempts
        return action.policy.retryable and action.attempts < action.policy.max_attempts

    def _apply_action_feedback(
        self,
        state: WorkflowState,
        result: HostActionResult,
    ) -> None:
        feedback = self._feedback_text(result)
        if feedback is not None:
            state.task.metadata["workflow_feedback"] = feedback
        if result.outcome == HostActionResultType.MODIFIED and feedback is not None:
            state.task.request = feedback

    def _feedback_text(self, result: HostActionResult) -> str | None:
        for key in ("request", "modified_request", "revision_request", "feedback"):
            value = result.metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        if result.error is not None and result.error.strip():
            return result.error.strip()
        return None
