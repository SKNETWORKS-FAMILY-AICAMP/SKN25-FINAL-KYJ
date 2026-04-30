from __future__ import annotations

from typing import Protocol

from ai_core.application.models.tasks import TaskEvent, TaskRequest, TaskSnapshot


class TaskStore(Protocol):
    def create(self, request: TaskRequest, snapshot: TaskSnapshot) -> None:
        """Persist a newly created workflow task."""
        ...

    def get(self, *, tenant: str, task_id: str) -> TaskSnapshot | None:
        """Return the current task snapshot if it exists."""
        ...

    def save(self, snapshot: TaskSnapshot) -> None:
        """Persist the current task snapshot."""
        ...

    def append_event(self, *, tenant: str, task_id: str, event: TaskEvent) -> None:
        """Append a workflow event for audit and streaming read models."""
        ...
