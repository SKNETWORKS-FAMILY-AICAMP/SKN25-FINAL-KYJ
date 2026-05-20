from __future__ import annotations

from dataclasses import dataclass, field

from foldmind_ai_core.core.application.commands.workflow import (
    AppendTaskInputCommand,
    CreateTaskCommand,
)
from foldmind_ai_core.core.application.errors import ResourceNotFoundError
from foldmind_ai_core.core.application.factories.workflow_commands import (
    task_context_from_command,
)
from foldmind_ai_core.core.application.factories.workflow_results import (
    task_result_from_snapshot,
)
from foldmind_ai_core.core.application.ports.outbound.task_repository import TaskRepository
from foldmind_ai_core.core.application.ports.outbound.workflow_runtime import WorkflowRuntime
from foldmind_ai_core.core.application.results.workflow import TaskResult
from foldmind_ai_core.core.domain.services.workflow_inputs import (
    WorkflowInputQueue,
)
from foldmind_ai_core.core.domain.models.workflow.tasks import (
    TaskAppendInput,
    TaskCreationInput,
)
from foldmind_ai_core.core.domain.services.workflow import (
    mark_workflow_failed,
    mark_workflow_result,
)
from foldmind_ai_core.shared.internal_ids import new_internal_id


@dataclass(slots=True)
class RunTaskUseCase:
    task_repository: TaskRepository
    workflow: WorkflowRuntime
    input_queue: WorkflowInputQueue = field(default_factory=WorkflowInputQueue)

    def execute(self, command: CreateTaskCommand | AppendTaskInputCommand) -> TaskResult:
        context = task_context_from_command(command.context)
        if isinstance(command, CreateTaskCommand):
            snapshot = self.input_queue.initial_snapshot(
                TaskCreationInput(
                    tenant=command.tenant,
                    request=command.request,
                    context=context,
                ),
                task_id=new_internal_id(),
            )
            self.task_repository.create(snapshot)
        else:
            existing_snapshot = self.task_repository.get(task_id=command.task_id)
            if existing_snapshot is None:
                raise ResourceNotFoundError(f"Task not found: {command.task_id}")
            snapshot = existing_snapshot
            self.input_queue.append_input(
                snapshot,
                TaskAppendInput(
                    task_id=command.task_id,
                    request=command.request,
                    context=context,
                ),
            )

        try:
            snapshot = self.workflow.run(snapshot)
            mark_workflow_result(snapshot)
        except Exception as exc:
            mark_workflow_failed(snapshot, exc)

        self.task_repository.save(snapshot)
        return task_result_from_snapshot(snapshot)
