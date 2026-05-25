from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from langgraph.graph import END
from langgraph.types import interrupt

from foldmind_ai_core.adapters.outbound.workflow_runtime import routes
from foldmind_ai_core.adapters.outbound.workflow_runtime.checkpoint_codec import (
    checkpoint_value,
    restore_checkpoint_value,
    workflow_state_from_checkpoint,
    workflow_state_to_checkpoint,
)
from foldmind_ai_core.adapters.outbound.workflow_runtime.graph_state import GraphState
from foldmind_ai_core.core.application.ports.outbound.runtime.workflow_runtime import (
    WorkflowActionType,
    WorkflowExecutionEngine,
    WorkflowState,
)
from foldmind_ai_core.core.domain.models.host_actions import HostActionResult
from foldmind_ai_core.core.domain.models.tasks import TaskStatus

_TERMINAL_TASK_STATUSES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.REJECTED,
}


@dataclass(slots=True)
class LangGraphWorkflowNodes:
    engine: WorkflowExecutionEngine

    async def plan(self, state: GraphState) -> GraphState:
        return await self.__map_state_async(state, self.engine.prepare)

    def route_step_node(self, state: GraphState) -> GraphState:
        return state

    def step(
        self,
        action_type: WorkflowActionType,
    ) -> Callable[[GraphState], Awaitable[GraphState]]:
        async def node(state: GraphState) -> GraphState:
            return await self.__run_step(state, expected_action_type=action_type)

        return node

    async def replan(self, state: GraphState) -> GraphState:
        return await self.__map_state_async(state, self.engine.replan)

    async def retry_step(self, state: GraphState) -> GraphState:
        return await self.__run_step(state, expected_action_type=None)

    def retry_host_action(self, state: GraphState) -> GraphState:
        return self.__map_state(state, self.engine.retry_host_action)

    def fail(self, state: GraphState) -> GraphState:
        return self.__map_state(state, self.engine.fail)

    def wait_for_host_action(self, state: GraphState) -> GraphState:
        workflow = workflow_state_from_checkpoint(state)
        result = interrupt(
            {
                "task_id": workflow.task.task_id,
                "tenant": workflow.task.tenant,
                "pending_actions": checkpoint_value(workflow.pending_actions),
            }
        )
        workflow.last_action_result = restore_checkpoint_value(result, HostActionResult)
        return workflow_state_to_checkpoint(workflow)

    def resume_from_action_result(self, state: GraphState) -> GraphState:
        workflow = workflow_state_from_checkpoint(state)
        if workflow.last_action_result is None:
            raise RuntimeError("Workflow resumed without an action result.")
        return workflow_state_to_checkpoint(
            self.engine.apply_action_result(workflow, workflow.last_action_result)
        )

    def route_step(self, state: GraphState) -> str:
        workflow = workflow_state_from_checkpoint(state)
        if not self.engine.has_next_step(workflow):
            return END
        if workflow.plan is None:
            raise RuntimeError("Workflow plan is not prepared.")
        return str(workflow.plan.steps[workflow.next_step_index].action_type)

    def route_after_step(self, state: GraphState) -> str:
        workflow = workflow_state_from_checkpoint(state)
        if workflow.task.status in _TERMINAL_TASK_STATUSES:
            return END
        if workflow.last_error is not None:
            return routes.RETRY_STEP if self.engine.can_retry_step(workflow) else routes.FAIL
        if workflow.pending_actions:
            return routes.WAIT_FOR_HOST_ACTION
        return routes.ROUTE_STEP if self.engine.has_next_step(workflow) else END

    def route_after_resume(self, state: GraphState) -> str:
        workflow = workflow_state_from_checkpoint(state)
        if workflow.task.status in _TERMINAL_TASK_STATUSES:
            return END
        if workflow.last_error is not None:
            return routes.FAIL
        if workflow.needs_replan:
            return routes.REPLAN
        if workflow.retry_action_id is not None:
            return routes.RETRY_HOST_ACTION
        if workflow.pending_actions:
            return routes.WAIT_FOR_HOST_ACTION
        return routes.ROUTE_STEP if self.engine.has_next_step(workflow) else END

    async def __run_step(
        self,
        state: GraphState,
        *,
        expected_action_type: WorkflowActionType | None,
    ) -> GraphState:
        workflow = workflow_state_from_checkpoint(state)
        workflow.failed_step_key = None
        workflow.last_error = None
        try:
            workflow = await self.engine.run_step(
                workflow,
                expected_action_type=expected_action_type,
            )
        except Exception as exc:
            workflow.last_error = str(exc)
            workflow.failed_step_key = self.engine.current_step_key(workflow)
            workflow.retry_counts[workflow.failed_step_key] = (
                workflow.retry_counts.get(workflow.failed_step_key, 0) + 1
            )
        return workflow_state_to_checkpoint(workflow)

    def __map_state(
        self,
        state: GraphState,
        update: Callable[[WorkflowState], WorkflowState],
    ) -> GraphState:
        return workflow_state_to_checkpoint(update(workflow_state_from_checkpoint(state)))

    async def __map_state_async(
        self,
        state: GraphState,
        update: Callable[[WorkflowState], Awaitable[WorkflowState]],
    ) -> GraphState:
        return workflow_state_to_checkpoint(
            await update(workflow_state_from_checkpoint(state))
        )
