from __future__ import annotations

from dataclasses import dataclass

from foldmind_ai_core.core.domain.models.host_actions import HostActionResult
from foldmind_ai_core.core.domain.models.tasks import TaskContext


@dataclass(slots=True)
class CreateTaskCommand:
    tenant: str
    request: str
    context: TaskContext


@dataclass(slots=True)
class AppendTaskInputCommand:
    task_id: str
    request: str
    context: TaskContext


@dataclass(frozen=True, slots=True)
class GetTaskQuery:
    task_id: str


@dataclass(frozen=True, slots=True)
class RemoveTaskInputCommand:
    task_input_id: str


@dataclass(frozen=True, slots=True)
class RecordActionResultCommand:
    result: HostActionResult
