from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.application.commands.workflow import RecordActionResultCommand
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.factories.workflow_commands import (
    host_action_result_from_command,
)
from foldmind_ai_core.core.application.factories.workflow_results import (
    record_action_result_from_snapshot,
)
from foldmind_ai_core.core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.core.application.ports.outbound.workflow_runtime import WorkflowRuntime
from foldmind_ai_core.core.application.results.workflow import RecordActionResult
from foldmind_ai_core.core.domain.services.workflow import (
    validate_host_action_result_for_action,
)


@dataclass(slots=True)
class RecordActionResultUseCase:
    task_repository: TaskRepository
    workflow: WorkflowRuntime

    def execute(self, command: RecordActionResultCommand) -> RecordActionResult:
        result = host_action_result_from_command(command.result)
        current_snapshot = self.task_repository.get_by_action_id(
            action_id=result.action_id
        )
        if current_snapshot is None:
            raise ResourceNotFoundError(f"Host action not found: {result.action_id}")
        current_action = next(
            (
                action
                for action in current_snapshot.host_actions
                if action.action_id == result.action_id
            ),
            None,
        )
        if current_action is None:
            raise ResourceNotFoundError(f"Host action not found: {result.action_id}")
        validate_host_action_result_for_action(current_action, result)

        snapshot = self.workflow.resume_from_action_result(
            task_id=current_snapshot.task_id,
            result=result,
        )
        self.task_repository.save(snapshot)
        return record_action_result_from_snapshot(recorded=True, snapshot=snapshot)
