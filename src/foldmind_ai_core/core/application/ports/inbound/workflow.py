from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.commands.workflow import (
    AppendTaskInputCommand,
    CreateTaskCommand,
    GetTaskQuery,
    RecordActionResultCommand,
    RemoveTaskInputCommand,
)
from foldmind_ai_core.core.application.results.workflow import (
    RecordActionResult,
    TaskResult,
)


class RunTaskInboundPort(Protocol):
    def execute(self, command: CreateTaskCommand | AppendTaskInputCommand) -> TaskResult:
        ...


class GetTaskInboundPort(Protocol):
    def execute(self, query: GetTaskQuery) -> TaskResult:
        ...


class RemoveTaskInputInboundPort(Protocol):
    def execute(self, command: RemoveTaskInputCommand) -> TaskResult:
        ...


class RecordActionResultInboundPort(Protocol):
    def execute(self, command: RecordActionResultCommand) -> RecordActionResult:
        ...
