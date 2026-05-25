from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.workflows.state.workflow_state import WorkflowState
from foldmind_ai_core.core.domain.models.host_actions import (
    HostAction,
    HostActionResult,
    HostActionResultType,
    HostActionStatus,
)
from foldmind_ai_core.core.domain.models.tasks import TaskStatus
from foldmind_ai_core.core.domain.services.workflow_domain_service import WorkflowDomainService


@dataclass(slots=True)
class HostActionResultService:
    workflow_rules: WorkflowDomainService = field(default_factory=WorkflowDomainService)

    def apply(self, state: WorkflowState, result: HostActionResult) -> WorkflowState:
        state.last_action_result = result
        state.needs_replan = False
        state.retry_action_id = None
        state.last_error = None
        self._apply_action_feedback(state, result)
        action = next(
            (
                candidate
                for candidate in state.task.host_actions
                if candidate.action_id == result.action_id
            ),
            None,
        )
        if action is not None:
            if self.workflow_rules.is_host_action_attempt_result(result):
                action.attempts += 1
            action.status = self.workflow_rules.host_action_status_for_result(
                action,
                result,
            )
            state.task.current_action_id = action.action_id
            state.needs_replan = result.outcome == HostActionResultType.MODIFIED
            if self.workflow_rules.should_schedule_host_action(action, result):
                state.retry_action_id = action.action_id
            if result.outcome == HostActionResultType.SUCCEEDED:
                output_error = self.workflow_rules.apply_successful_host_action_output(
                    action,
                    state.task.host_actions,
                    result,
                )
                if output_error is not None:
                    action.status = HostActionStatus.FAILED
                    state.task.error = output_error

        state.pending_actions = [
            action
            for action in state.pending_actions
            if action.action_id != result.action_id
            and self.workflow_rules.is_pending_host_action(action)
        ]
        self.schedule_next_action(state)
        if state.pending_actions:
            state.task.current_action_id = state.pending_actions[0].action_id

        self._apply_task_status(state, result)
        return state

    def _apply_task_status(self, state: WorkflowState, result: HostActionResult) -> None:
        if state.needs_replan:
            state.pending_actions = []
            state.task.current_action_id = None
            state.task.status = TaskStatus.CLARIFICATION_REQUIRED
            state.task.analysis.message = "Task needs replanning."
            return

        if result.outcome == HostActionResultType.REJECTED:
            state.pending_actions = []
            state.task.current_action_id = None
            state.task.status = TaskStatus.REJECTED
            state.task.analysis.message = "Task rejected."
            return

        if self._any_host_action_failed(state):
            state.pending_actions = []
            state.task.current_action_id = None
            state.task.status = TaskStatus.FAILED
            state.task.error = state.task.error or result.error or "Host action failed."
            state.task.analysis.message = "Task failed."
            return

        if self._all_host_actions_completed(state):
            state.task.current_action_id = None
            state.task.status = TaskStatus.COMPLETED
            state.task.analysis.message = "Task completed."
            return

        pending_proposed_action = self._first_pending_action_with_status(
            state,
            HostActionStatus.PROPOSED,
        )
        pending_ready_action = self._first_pending_action_with_status(
            state,
            HostActionStatus.READY,
        )
        has_pending_host_execution = (
            state.retry_action_id is not None or pending_ready_action is not None
        )
        if has_pending_host_execution:
            retry_requested = (
                state.retry_action_id is not None
                and self.workflow_rules.is_host_action_retry_result(result)
            )
            state.task.status = TaskStatus.READY_FOR_HOST_ACTION
            if pending_ready_action is not None:
                state.task.current_action_id = pending_ready_action.action_id
            state.task.analysis.message = (
                "Host action retry requested."
                if retry_requested
                else "Task is ready for host action."
            )
            return
        proposed_action = pending_proposed_action or self._first_proposed_action(state)
        if proposed_action is not None:
            state.task.status = TaskStatus.AWAITING_DECISION
            state.task.current_action_id = proposed_action.action_id
            state.task.analysis.message = "Task is awaiting a host action decision."
            return
        if result.outcome == HostActionResultType.FAILED:
            state.task.status = TaskStatus.FAILED
            state.task.error = result.error
            state.task.analysis.message = "Task failed."

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
            state.task.analysis.message = (
                "Host action retry scheduled."
                if self.workflow_rules.is_host_action_retry_result(
                    state.last_action_result
                )
                else "Task is ready for host action."
            )
            break
        return state

    def merge_host_actions(self, state: WorkflowState, actions: list[HostAction]) -> None:
        existing_action_ids = {action.action_id for action in state.task.host_actions}
        for action in actions:
            action_id = action.action_id
            if action_id in existing_action_ids:
                continue
            state.task.host_actions.append(action)
            existing_action_ids.add(action_id)
        self.schedule_next_action(state)

    def schedule_next_action(self, state: WorkflowState) -> None:
        state.pending_actions = []
        for action in state.task.host_actions:
            if self.workflow_rules.is_completed_host_action_status(action.status):
                continue
            if (
                action.status == HostActionStatus.PROPOSED
                and not action.policy.requires_confirmation
            ):
                action.status = HostActionStatus.READY
            if not self.workflow_rules.is_pending_host_action(action):
                continue
            state.pending_actions.append(action)
            return

    def _all_host_actions_completed(self, state: WorkflowState) -> bool:
        return bool(state.task.host_actions) and all(
            self.workflow_rules.is_completed_host_action_status(action.status)
            for action in state.task.host_actions
        )

    def _any_host_action_failed(self, state: WorkflowState) -> bool:
        return any(
            action.status == HostActionStatus.FAILED
            for action in state.task.host_actions
        )

    def _first_proposed_action(self, state: WorkflowState) -> HostAction | None:
        return next(
            (
                action
                for action in state.task.host_actions
                if action.status == HostActionStatus.PROPOSED
            ),
            None,
        )

    def _first_pending_action_with_status(
        self,
        state: WorkflowState,
        status: HostActionStatus,
    ) -> HostAction | None:
        return next(
            (
                action
                for action in state.pending_actions
                if action.status == status
            ),
            None,
        )

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
