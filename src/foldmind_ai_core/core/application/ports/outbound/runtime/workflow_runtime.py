from __future__ import annotations

from typing import Protocol

from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowArtifactName as WorkflowArtifactName,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowArtifacts as WorkflowArtifacts,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowExecutionPlan as WorkflowExecutionPlan,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowExecutionTrace as WorkflowExecutionTrace,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowStep as WorkflowStep,
)
from foldmind_ai_core.core.application.workflows.state.execution import (
    WorkflowStepInput as WorkflowStepInput,
)
from foldmind_ai_core.core.application.workflows.state.plan import (
    WorkflowActionType as WorkflowActionType,
)
from foldmind_ai_core.core.application.workflows.state.workflow_state import (
    WorkflowState as WorkflowState,
)
from foldmind_ai_core.core.domain.models.host_actions import HostActionResult
from foldmind_ai_core.core.domain.models.tasks import TaskSnapshot


class WorkflowRuntime(Protocol):
    async def run(self, snapshot: TaskSnapshot) -> TaskSnapshot:
        """Run a workflow from the initial task snapshot."""
        ...

    async def resume_from_action_result(
        self,
        *,
        task_id: str,
        result: HostActionResult,
    ) -> TaskSnapshot:
        """Resume a paused workflow after the host reports an action result."""
        ...


class WorkflowExecutionEngine(Protocol):
    async def prepare(self, state: WorkflowState) -> WorkflowState:
        ...

    async def replan(self, state: WorkflowState) -> WorkflowState:
        ...

    def retry_host_action(self, state: WorkflowState) -> WorkflowState:
        ...

    def fail(self, state: WorkflowState) -> WorkflowState:
        ...

    def has_next_step(self, state: WorkflowState) -> bool:
        ...

    async def run_step(
        self,
        state: WorkflowState,
        *,
        expected_action_type: WorkflowActionType | None,
    ) -> WorkflowState:
        ...

    def can_retry_step(self, state: WorkflowState) -> bool:
        ...

    def apply_action_result(
        self,
        state: WorkflowState,
        result: HostActionResult,
    ) -> WorkflowState:
        ...

    def current_step_key(self, state: WorkflowState) -> str:
        ...
