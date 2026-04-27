from __future__ import annotations

from dataclasses import dataclass, field

from ai_core.common.types import Metadata
from ai_core.domain.tasks import TaskSnapshot


@dataclass(slots=True)
class CreateTaskRequest:
    task_id: str
    tenant: str
    request: str
    user_id: str | None = None
    request_id: str | None = None
    conversation_id: str | None = None
    context: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class TaskSnapshotResponse:
    task: TaskSnapshot
