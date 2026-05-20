from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.domain.models.workflow.actions import HostActionResult
from foldmind_ai_core.core.domain.models.workflow.tasks import TaskSnapshot


class WorkflowRuntime(Protocol):
    def run(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        """Run a workflow from the initial task snapshot."""
        ...

    def resume_from_action_result(
        self,
        *,
        task_id: str,
        result: HostActionResult,
    ) -> TaskSnapshot:
        """Resume a paused workflow after the host reports an action result."""
        ...
