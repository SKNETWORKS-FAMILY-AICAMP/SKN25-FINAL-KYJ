from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.models.task_commands import (
    AppendTaskInputCommand,
    CreateTaskCommand,
    GetTaskQuery,
    RecordActionResultCommand,
    RemoveTaskInputCommand,
)
from foldmind_ai_core.core.application.models.task_results import (
    RecordActionResult,
)
from foldmind_ai_core.core.domain.models.tasks import TaskSnapshot


class TaskWorkflowServicePort(Protocol):
    async def create_task(self, command: CreateTaskCommand) -> TaskSnapshot:
        ...

    async def append_task_input(
        self,
        command: AppendTaskInputCommand,
    ) -> TaskSnapshot:
        ...

    async def get_task(self, query: GetTaskQuery) -> TaskSnapshot:
        ...

    async def remove_task_input(
        self,
        command: RemoveTaskInputCommand,
    ) -> TaskSnapshot:
        ...

    async def record_action_result(
        self,
        command: RecordActionResultCommand,
    ) -> RecordActionResult:
        ...
