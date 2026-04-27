from __future__ import annotations

from dataclasses import dataclass

from ai_core.workflows.executor import WorkflowExecutor
from ai_core.workflows.state import WorkflowState


@dataclass(slots=True)
class WorkflowGraph:
    executor: WorkflowExecutor

    def run(self, state: WorkflowState) -> WorkflowState:
        return self.executor.execute(state)
