from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.domain.workflow.tasks import TaskSnapshot


class TaskRepository(Protocol):
    def create(self, snapshot: TaskSnapshot) -> None:
        """Persist a newly created workflow task."""
        ...

    def get(self, *, task_id: str) -> TaskSnapshot | None:
        """Return the current task snapshot if it exists."""
        ...

    def get_by_request_id(self, *, task_request_id: str) -> TaskSnapshot | None:
        """Return the task that owns a globally unique request id."""
        ...

    def get_by_action_id(self, *, action_id: str) -> TaskSnapshot | None:
        """Return the task that owns a globally unique host action id."""
        ...

    def save(self, snapshot: TaskSnapshot) -> None:
        """Persist the current task snapshot."""
        ...
