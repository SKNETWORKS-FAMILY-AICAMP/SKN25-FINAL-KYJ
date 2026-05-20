from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.commands.workflow import RemoveTaskInputCommand
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.factories.workflow_results import (
    task_result_from_snapshot,
)
from foldmind_ai_core.core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.core.application.ports.outbound.workflow_runtime import WorkflowRuntime
from foldmind_ai_core.core.application.results.workflow import TaskResult
from foldmind_ai_core.core.domain.services.workflow import (
    mark_workflow_failed,
    mark_workflow_result,
)
from foldmind_ai_core.core.domain.services.workflow_inputs import WorkflowInputQueue


@dataclass(slots=True)
class RemoveTaskInputUseCase:
    task_repository: TaskRepository
    workflow: WorkflowRuntime
    input_queue: WorkflowInputQueue = field(default_factory=WorkflowInputQueue)

    def execute(self, command: RemoveTaskInputCommand) -> TaskResult:
        snapshot = self.task_repository.get_by_input_id(
            task_input_id=command.task_input_id
        )
        if snapshot is None:
            raise ResourceNotFoundError(f"Task input not found: {command.task_input_id}")

        should_replan = self.input_queue.remove_input(
            snapshot,
            command.task_input_id,
        )
        if not should_replan:
            self.task_repository.save(snapshot)
            return task_result_from_snapshot(snapshot)

        try:
            snapshot = self.workflow.run(snapshot)
            mark_workflow_result(snapshot)
        except Exception as exc:
            mark_workflow_failed(snapshot, exc)
        self.task_repository.save(snapshot)
        return task_result_from_snapshot(snapshot)
