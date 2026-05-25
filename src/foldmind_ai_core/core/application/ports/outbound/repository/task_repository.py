from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.tasks import TaskSnapshot


class TaskRepositoryPort(Protocol):
    async def create(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        """Persist a newly created workflow task."""
        ...

    async def get(self, *, task_id: str) -> TaskSnapshot | None:
        """Return the current task snapshot if it exists."""
        ...

    async def get_by_input_id(
        self,
        *,
        task_input_id: str,
    ) -> TaskSnapshot | None:
        """Return the input owner's task snapshot."""
        ...

    async def get_by_action_id(
        self,
        *,
        action_id: str,
    ) -> TaskSnapshot | None:
        """Return the action owner's task snapshot."""
        ...

    async def save_if_unchanged(
        self,
        snapshot: TaskSnapshot,
        *,
        expected_snapshot: TaskSnapshot,
    ) -> bool:
        """Persist the snapshot only if the task still matches the expected snapshot."""
        ...
