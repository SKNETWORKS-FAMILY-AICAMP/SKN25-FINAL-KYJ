from __future__ import annotations

from dataclasses import dataclass

from ai_core.workflows.state import WorkflowState


@dataclass(slots=True)
class WorkflowExecutor:
    def execute(self, state: WorkflowState) -> WorkflowState:
        return state
