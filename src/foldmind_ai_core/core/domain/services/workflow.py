from __future__ import annotations

from typing import TYPE_CHECKING

from foldmind_ai_core.shared.validation import InvalidInputError

if TYPE_CHECKING:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        HostAction,
        HostActionResult,
        HostActionResultType,
        HostActionStatus,
    )
    from foldmind_ai_core.core.domain.models.workflow.tasks import TaskSnapshot


def validate_host_action_policy(*, max_attempts: int) -> None:
    if (
        isinstance(max_attempts, bool)
        or not isinstance(max_attempts, int)
        or max_attempts <= 0
    ):
        raise InvalidInputError("max_attempts must be a positive integer.")


def validate_host_action_attempts(attempts: int) -> None:
    if isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 0:
        raise InvalidInputError("attempts must be a non-negative integer.")


def mark_workflow_result(snapshot: TaskSnapshot) -> None:
    from foldmind_ai_core.core.domain.models.workflow.actions import HostActionStatus
    from foldmind_ai_core.core.domain.models.workflow.tasks import TaskOutputType, TaskStatus

    if snapshot.status in {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.REJECTED,
    }:
        return

    if (
        snapshot.result is not None
        and snapshot.result.result_type == TaskOutputType.CLARIFICATION
    ):
        snapshot.status = TaskStatus.CLARIFICATION_REQUIRED
        snapshot.current_action_id = None
        snapshot.analysis.message = "Task requires clarification."
        return

    proposed_action_id: str | None = None
    for action in snapshot.host_actions:
        if is_completed_host_action_status(action.status):
            continue
        if action.status == HostActionStatus.FAILED:
            snapshot.status = TaskStatus.FAILED
            snapshot.current_action_id = None
            snapshot.error = snapshot.error or "Host action failed."
            snapshot.analysis.message = "Task failed."
            return
        if (
            action.status == HostActionStatus.PROPOSED
            and not action.policy.requires_confirmation
        ):
            action.status = HostActionStatus.READY
        if action.status == HostActionStatus.READY:
            snapshot.status = TaskStatus.READY_FOR_HOST_ACTION
            snapshot.current_action_id = action.action_id
            snapshot.analysis.message = "Task is ready for host action."
            return
        if action.status == HostActionStatus.PROPOSED and proposed_action_id is None:
            proposed_action_id = action.action_id

    if proposed_action_id is not None:
        snapshot.status = TaskStatus.AWAITING_DECISION
        snapshot.current_action_id = proposed_action_id
        snapshot.analysis.message = "Task is awaiting a host action decision."
        return

    snapshot.status = TaskStatus.COMPLETED
    snapshot.current_action_id = None
    snapshot.analysis.message = "Task completed."


def mark_workflow_failed(snapshot: TaskSnapshot, exc: Exception) -> None:
    from foldmind_ai_core.core.domain.models.workflow.actions import HostActionStatus
    from foldmind_ai_core.core.domain.models.workflow.tasks import TaskAnalysis, TaskStatus

    snapshot.status = TaskStatus.FAILED
    snapshot.error = str(exc)
    snapshot.current_action_id = None
    snapshot.analysis = TaskAnalysis(message="Task failed.")
    for action in snapshot.host_actions:
        if action.status in {
            HostActionStatus.PROPOSED,
            HostActionStatus.READY,
        }:
            action.status = HostActionStatus.FAILED


def validate_host_action_result_for_action(
    action: HostAction,
    result: HostActionResult,
) -> None:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        HostActionResultType,
    )

    if result.action_type is not None and result.action_type != action.action_type:
        raise InvalidInputError(
            "Host action result type does not match the recorded action."
        )
    if (
        result.outcome == HostActionResultType.SUCCEEDED
        and result.error is not None
        and result.error.strip()
    ):
        raise InvalidInputError("Succeeded host action results must not include error.")
    if result.output is not None and result.outcome != HostActionResultType.SUCCEEDED:
        raise InvalidInputError("Only succeeded host action results may include output.")
    allowed_outcomes = _allowed_outcomes_for_status(action.status)
    if allowed_outcomes is None:
        raise InvalidInputError("Host action is not awaiting a result.")
    if result.outcome not in allowed_outcomes:
        raise InvalidInputError(
            "Host action result outcome is not valid for the recorded action status."
        )


def is_host_action_attempt_result(result: HostActionResult) -> bool:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        HostActionResultType,
    )

    return result.outcome in {
        HostActionResultType.SUCCEEDED,
        HostActionResultType.FAILED,
        HostActionResultType.RETRY,
    }


def is_host_action_retry_result(result: HostActionResult | None) -> bool:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        HostActionResultType,
    )

    return result is not None and result.outcome in {
        HostActionResultType.FAILED,
        HostActionResultType.RETRY,
    }


def is_completed_host_action_status(status: HostActionStatus) -> bool:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        HostActionStatus,
    )

    return status in {
        HostActionStatus.SUCCEEDED,
        HostActionStatus.SKIPPED,
    }


def host_action_status_for_result(
    action: HostAction,
    result: HostActionResult,
) -> HostActionStatus:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        HostActionResultType,
        HostActionStatus,
    )

    if result.outcome == HostActionResultType.SUCCEEDED:
        return HostActionStatus.SUCCEEDED
    if result.outcome == HostActionResultType.APPROVED:
        return HostActionStatus.READY
    if result.outcome == HostActionResultType.SKIPPED:
        return (
            HostActionStatus.SKIPPED
            if action.policy.allow_skip
            else HostActionStatus.FAILED
        )
    if result.outcome in {
        HostActionResultType.REJECTED,
        HostActionResultType.MODIFIED,
    }:
        return HostActionStatus.SKIPPED
    if (
        result.outcome in {HostActionResultType.FAILED, HostActionResultType.RETRY}
        and can_retry_host_action(action, result)
    ):
        return HostActionStatus.READY
    return HostActionStatus.FAILED


def should_schedule_host_action(
    action: HostAction,
    result: HostActionResult,
) -> bool:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        HostActionResultType,
    )

    return result.outcome == HostActionResultType.APPROVED or (
        result.outcome in {HostActionResultType.FAILED, HostActionResultType.RETRY}
        and can_retry_host_action(action, result)
    )


def can_retry_host_action(
    action: HostAction,
    result: HostActionResult,
) -> bool:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        HostActionResultType,
    )

    return action.attempts < action.policy.max_attempts and (
        result.outcome == HostActionResultType.RETRY or action.policy.retryable
    )


def is_pending_host_action(action: HostAction) -> bool:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        HostActionStatus,
    )

    return action.status == HostActionStatus.READY or (
        action.status == HostActionStatus.PROPOSED and action.policy.requires_confirmation
    )


def apply_successful_host_action_output(
    completed_action: HostAction,
    actions: list[HostAction],
    result: HostActionResult,
) -> str | None:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        CreateDocumentInput,
        CreateDocumentOutput,
        CreateFolderOutput,
        HostActionType,
        LinkDocumentsInput,
    )

    if completed_action.action_type == HostActionType.CREATE_FOLDER:
        completed_index = _host_action_index(completed_action, actions)
        dependent_document_inputs = [
            candidate.input
            for index, candidate in enumerate(actions)
            if index > completed_index
            and isinstance(candidate.input, CreateDocumentInput)
            and candidate.input.folder_id is None
            and candidate.input.metadata.get("folder_action_id")
            == completed_action.action_id
        ]
        if not dependent_document_inputs:
            return None
        if not isinstance(result.output, CreateFolderOutput):
            return "Create folder output is required for dependent document actions."
        for document_input in dependent_document_inputs:
            document_input.folder_id = result.output.folder_id
        return None

    if completed_action.action_type == HostActionType.CREATE_DOCUMENT:
        completed_index = _host_action_index(completed_action, actions)
        dependent_link_inputs = [
            candidate.input
            for index, candidate in enumerate(actions)
            if index > completed_index
            and isinstance(candidate.input, LinkDocumentsInput)
            and candidate.input.source_id == completed_action.action_id
        ]
        if not dependent_link_inputs:
            return None
        if not isinstance(result.output, CreateDocumentOutput):
            return "Create document output is required for dependent link actions."
        for link_input in dependent_link_inputs:
            link_input.source_type = result.output.created_document_type
            link_input.source_id = result.output.created_document_id
            if result.output.source_version is not None:
                link_input.metadata["source_version"] = result.output.source_version
    return None


def _host_action_index(action: HostAction, actions: list[HostAction]) -> int:
    for index, candidate in enumerate(actions):
        if candidate.action_id == action.action_id:
            return index
    return len(actions)


def _allowed_outcomes_for_status(
    status: HostActionStatus,
) -> set[HostActionResultType] | None:
    from foldmind_ai_core.core.domain.models.workflow.actions import (
        HostActionResultType,
        HostActionStatus,
    )

    if status == HostActionStatus.PROPOSED:
        return {
            HostActionResultType.APPROVED,
            HostActionResultType.REJECTED,
            HostActionResultType.MODIFIED,
            HostActionResultType.SKIPPED,
        }
    if status == HostActionStatus.READY:
        return {
            HostActionResultType.SUCCEEDED,
            HostActionResultType.FAILED,
            HostActionResultType.RETRY,
            HostActionResultType.SKIPPED,
            HostActionResultType.REJECTED,
            HostActionResultType.MODIFIED,
        }
    return None
